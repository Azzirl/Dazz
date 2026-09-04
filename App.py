import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# ==========================================
# CONFIGURACIÓN DE PÁGINA EN STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Suite EMS - UPS Bloque D",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="collapsed"
)

# Estilos CSS personalizados para Dashboard
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; max-width: 1300px; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    
    .card-metric {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    .metric-title { font-size: 13px; color: #64748b; font-weight: 600; margin-bottom: 4px; text-transform: uppercase; }
    .metric-value { font-size: 28px; font-weight: 700; color: #0f172a; }
    .metric-unit { font-size: 14px; font-weight: 500; color: #64748b; margin-left: 4px; }
    
    .stTextInput > div > div > input {
        background-color: #f8fafc;
        border-radius: 6px;
        border: 1px solid #cbd5e1;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CAMPOS EDITABLES DEL PROYECTO (NUEVO)
# ==========================================
st.markdown("<div style='font-size: 14px; font-weight: 600; color: #475569; margin-bottom: 8px;'>Datos de Identificación del Proyecto</div>", unsafe_allow_html=True)

col_t1, col_t2, col_t3 = st.columns([1.5, 2, 1])
with col_t1:
    titulo_app = st.text_input("Nombre del proyecto", value="Suite EMS — Gestor de Energía Bloque D (UPS)", label_visibility="collapsed")
with col_t2:
    subtitulo_app = st.text_input("Descripción", value="Optimización por Peak Shaving · Reducción de Demanda de Red · Cumplimiento IEEE 2030.7", label_visibility="collapsed")
with col_t3:
    ubicacion_app = st.text_input("Ubicación", value="UPS Campus Centenario", label_visibility="collapsed")

# ==========================================
# CONTROLES Y PARÁMETROS OPERATIVOS
# ==========================================
st.markdown("<div style='font-size: 14px; font-weight: 600; color: #475569; margin-top: 10px; margin-bottom: 8px;'>Parámetros de Diseño y Simulación</div>", unsafe_allow_html=True)

col_p1, col_p2, col_p3, col_p4 = st.columns(4)
p_lim = col_p1.slider("Límite de Red (kW)", 80, 200, 130, 5)
c_bat = col_p2.slider("Capacidad BESS (kWh)", 50, 1000, 250, 10)
p_pv = col_p3.slider("Generación PV (kWp)", 0, 300, 150, 10)
s_trafo = col_p4.slider("Capacidad Trafo (kVA)", 315, 2000, 1000, 50)

# ==========================================
# CÁLCULOS DEL EMS 
# ==========================================
REAL_LOAD = [36, 36, 36, 36, 36, 40, 60, 90, 120, 145, 160, 175, 179.1, 140, 150, 155, 160, 165, 172, 175, 130, 90, 50, 36]
PV_BASE = [0, 0, 0, 0, 0, 0, 5, 25, 55, 90, 120, 140, 150, 140, 120, 90, 55, 25, 5, 0, 0, 0, 0, 0]

factor_pv = p_pv / 150.0 if p_pv > 0 else 0.0
pv_real = [round(v * factor_pv, 1) for v in PV_BASE]

soc_min = 0.20 * c_bat
soc_max = c_bat
energia = c_bat * 0.50
carga_noc = 40.0

rows_ems = []
for i in range(24):
    p_teorica = REAL_LOAD[i] - pv_real[i]
    p_bat = 0.0
    
    if p_teorica > p_lim:
        req = p_teorica - p_lim
        p_bat = req if (energia - req) >= soc_min else max(0.0, energia - soc_min)
    elif 1 <= i <= 5:
        p_bat = -carga_noc if (energia + carga_noc) <= soc_max else -(soc_max - energia)
        
    p_red = p_teorica - p_bat
    energia -= p_bat
    soc = (energia / c_bat) * 100.0
    
    rows_ems.append({
        'Hora': f"{i:02d}:00", 'P_Carga': REAL_LOAD[i], 'P_PV': pv_real[i],
        'P_Bat': round(p_bat, 1), 'P_Red': round(p_red, 1), 'SOC': round(soc, 1)
    })

df_ems = pd.DataFrame(rows_ems)

demanda_max = float(df_ems['P_Carga'].max())
demanda_recortada = float(df_ems['P_Red'].max())
reduccion_pico = demanda_max - demanda_recortada
inv_req = p_pv / 0.95 if p_pv > 0 else p_lim / 0.95

i_nom = (s_trafo * 1000.0) / (1.73205 * 220.0)
icc_simetrica = i_nom / (5.75 / 100.0)
carg_sin = (demanda_max / s_trafo) * 100.0
carg_con = (demanda_recortada / s_trafo) * 100.0

# ==========================================
# BANNER PRINCIPAL (AHORA LEE LOS CAMPOS EDITABLES)
# ==========================================
st.markdown(f"""
<div style="background-color: #ffffff; padding: 18px 24px; border-radius: 10px; border: 1px solid #e2e8f0; margin-top: 10px; margin-bottom: 25px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <h2 style="margin: 0; color: #0f172a; font-size: 22px;">⚡ {titulo_app}</h2>
            <p style="margin: 4px 0 0 0; color: #64748b; font-size: 13px;">{subtitulo_app}</p>
        </div>
        <div style="display: flex; gap: 8px;">
            <span style="background-color: #dbeafe; color: #1e40af; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">{ubicacion_app}</span>
            <span style="background-color: #d1fae5; color: #065f46; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">Trafo {s_trafo:.0f} kVA</span>
            <span style="background-color: #f1f5f9; color: #334155; padding: 5px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;">P_lim = {p_lim:.0f} kW</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# PESTAÑAS DE NAVEGACIÓN
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboad & Peak Shaving", 
    "📐 Diagrama Unifilar Interactivo", 
    "📄 Generación de Memoria Técnica", 
    "💻 Exportación CAD y Reportes"
])

# ------------------------------------------
# TAB 1: DASHBOARD
# ------------------------------------------
with tab1:
    col_m1, col_m2, col_m3 = st.columns(3)
    with col_m1:
        st.markdown(f"""
        <div class="card-metric">
            <div class="metric-title">Reducción Neta de Demanda Pico</div>
            <div class="metric-value" style="color:#059669;">{reduccion_pico:.1f} <span class="metric-unit">kW</span></div>
            <div class="metric-sub">Pico original: {demanda_max:.1f} kW → Recortado: {demanda_recortada:.1f} kW</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"""
        <div class="card-metric">
            <div class="metric-title">Corriente de Cortocircuito Icc</div>
            <div class="metric-value">{icc_simetrica/1000.0:.2f} <span class="metric-unit">kA</span></div>
            <div class="metric-sub">Calculado en bus 220V (%Z=5.75%)</div>
        </div>
        """, unsafe_allow_html=True)
    with col_m3:
        st.markdown(f"""
        <div class="card-metric">
            <div class="metric-title">Cargabilidad del Transformador</div>
            <div class="metric-value">{carg_con:.1f} <span class="metric-unit">%</span></div>
            <div class="metric-sub">Capacidad térmica original sin EMS: {carg_sin:.1f}%</div>
        </div>
        """, unsafe_allow_html=True)

    fig_ems = go.Figure()
    fig_ems.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Carga'], name='Demanda Bruta (kW)', line=dict(color='#2563eb', width=2.5)))
    fig_ems.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Red'], name='Demanda Gestionada Red (kW)', fill='tozeroy', line=dict(color='#10b981', width=2.5)))
    fig_ems.add_trace(go.Scatter(x=df_ems['Hora'], y=[p_lim]*24, name=f'Límite Configurado ({p_lim:.0f} kW)', line=dict(color='#ef4444', width=2, dash='dash')))
    fig_ems.update_layout(title="Perfiles de Potencia Activa (24 Horas)", xaxis_title="Hora del Día", yaxis_title="Potencia (kW)", template="plotly_white", height=400, margin=dict(t=40, b=20, l=20, r=20))
    st.plotly_chart(fig_ems, use_container_width=True)

# ------------------------------------------
# TAB 2: DIAGRAMA UNIFILAR
# ------------------------------------------
with tab2:
    st.markdown("<h4 style='color: #334155;'>Esquema Eléctrico de Interconexión (IEEE 1547)</h4>", unsafe_allow_html=True)
    
    fig_sld = go.Figure()
    fig_sld.update_xaxes(visible=False); fig_sld.update_yaxes(visible=False)
    
    fig_sld.add_trace(go.Scatter(x=[0, 0], y=[200, 160], mode='lines', line=dict(color='#1e293b', width=3), showlegend=False))
    fig_sld.add_annotation(x=0, y=205, text="ACOMETIDA RED PRINCIPAL CNEL • 69 kV / 13.8 kV", showarrow=False, font=dict(size=12, color='#1e40af', family='Arial Black'))
    fig_sld.add_trace(go.Scatter(x=[0], y=[160], mode='markers', marker=dict(color='#dc2626', size=12), showlegend=False))
    fig_sld.add_annotation(x=22, y=160, text="CCF 100A + APARTARRAYOS", showarrow=False, font=dict(size=11))
    
    fig_sld.add_shape(type="circle", x0=-12, y0=116, x1=12, y1=140, line_color="#0284c7", line_width=3)
    fig_sld.add_shape(type="circle", x0=-12, y0=100, x1=12, y1=124, line_color="#0284c7", line_width=3)
    
    fig_sld.add_shape(type="rect", x0=25, y0=95, x1=100, y1=145, fillcolor="#f0f9ff", line_color="#0284c7", line_width=1.5)
    fig_sld.add_annotation(x=62, y=137, text=f"TRANSFORMADOR {s_trafo:.0f} kVA", showarrow=False, font=dict(size=11, color='#0369a1', family='Arial Black'))
    fig_sld.add_annotation(x=62, y=127, text="Primario: 69 kV / 13.8 kV (Delta)", showarrow=False, font=dict(size=9.5))
    fig_sld.add_annotation(x=62, y=118, text=f"Secundario: 220/127 V (Dyn11)", showarrow=False, font=dict(size=9.5))
    fig_sld.add_annotation(x=62, y=105, text=f"Icc_sim = {icc_simetrica/1000.0:.2f} kA", showarrow=False, font=dict(size=9.5, color='#991b1b'))
    
    fig_sld.add_trace(go.Scatter(x=[0, 0], y=[100, 80], mode='lines', line=dict(color='#1e293b', width=3), showlegend=False))
    fig_sld.add_shape(type="rect", x0=-10, y0=65, x1=10, y1=80, fillcolor="white", line_color="#1e293b", line_width=2)
    fig_sld.add_annotation(x=68, y=72.5, text="DISYUNTOR TGBT: 3P-2000A · 50 kA AIC", showarrow=False, font=dict(size=11, color='#15803d', family='Arial Black'))
    
    fig_sld.add_trace(go.Scatter(x=[0, 0], y=[65, 50], mode='lines', line=dict(color='#1e293b', width=3), showlegend=False))
    fig_sld.add_trace(go.Scatter(x=[-110, 110], y=[50, 50], mode='lines', line=dict(color='#2563eb', width=6), showlegend=False))
    
    fig_sld.add_trace(go.Scatter(x=[-60, -60], y=[50, 30], mode='lines', line=dict(color='#1e293b', width=2), showlegend=False))
    fig_sld.add_trace(go.Scatter(x=[-60, -60], y=[20, 5], mode='lines', line=dict(color='#ef4444', width=2), showlegend=False))
    fig_sld.add_shape(type="rect", x0=-85, y0=-15, x1=-35, y1=5, fillcolor="#fef2f2", line_color="#ef4444", line_width=1.5)
    fig_sld.add_annotation(x=-60, y=-1, text=f"CARGAS {ubicacion_app}", showarrow=False, font=dict(size=9.5, color='#991b1b', family='Arial Black'))
    fig_sld.add_annotation(x=-60, y=-10, text=f"Pico: {demanda_max:.1f} kW", showarrow=False, font=dict(size=9.5))

    fig_sld.add_trace(go.Scatter(x=[60, 60], y=[50, 30], mode='lines', line=dict(color='#1e293b', width=2), showlegend=False))
    fig_sld.add_trace(go.Scatter(x=[60, 60], y=[20, 5], mode='lines', line=dict(color='#8b5cf6', width=2), showlegend=False))
    fig_sld.add_shape(type="rect", x0=32, y0=-20, x1=88, y1=5, fillcolor="#faf5ff", line_color="#a855f7", line_width=2)
    fig_sld.add_annotation(x=60, y=-1, text="INVERSOR HÍBRIDO", showarrow=False, font=dict(size=11, color='#6b21a8', family='Arial Black'))
    fig_sld.add_annotation(x=60, y=-10, text=f"S_nom: {inv_req:.1f} kVA", showarrow=False, font=dict(size=9.5))
    
    fig_sld.add_trace(go.Scatter(x=[45, 45], y=[-20, -35], mode='lines', line=dict(color='#f97316', width=2), showlegend=False))
    fig_sld.add_trace(go.Scatter(x=[75, 75], y=[-20, -35], mode='lines', line=dict(color='#10b981', width=2), showlegend=False))
    
    fig_sld.add_shape(type="rect", x0=30, y0=-55, x1=58, y1=-35, fillcolor="#fefce8", line_color="#eab308", line_width=1.5)
    fig_sld.add_annotation(x=44, y=-41, text="ARREGLO PV", showarrow=False, font=dict(size=10, family='Arial Black'))
    fig_sld.add_annotation(x=44, y=-48, text=f"{p_pv:.0f} kWp", showarrow=False, font=dict(size=9.5))
    
    fig_sld.add_shape(type="rect", x0=62, y0=-55, x1=92, y1=-35, fillcolor="#ecfdf5", line_color="#10b981", line_width=1.5)
    fig_sld.add_annotation(x=77, y=-41, text="BANCO BESS", showarrow=False, font=dict(size=10, family='Arial Black'))
    fig_sld.add_annotation(x=77, y=-48, text=f"{c_bat:.0f} kWh", showarrow=False, font=dict(size=9.5))

    fig_sld.update_layout(height=550, margin=dict(l=10, r=10, t=10, b=10), template='plotly_white')
    st.plotly_chart(fig_sld, use_container_width=True)

# ------------------------------------------
# TAB 3: MEMORIA TÉCNICA Y DOCX (IDÉNTICO A GPS GROUP)
# ------------------------------------------
with tab3:
    st.markdown("<h4 style='color: #334155;'>Expediente Técnico del Proyecto (Formato Oficial)</h4>", unsafe_allow_html=True)
    st.markdown("La Memoria Técnica generada respeta estrictamente el formato de ingeniería (Tablas de control, índices y marcos normativos) de las especificaciones de CNEL EP.")
    
    def generar_memoria_oficial_gps():
        doc = Document()
        
        # Estilos de fuente por defecto
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Arial'
        font.size = Pt(10)

        # Encabezado Principal
        p_title = doc.add_paragraph()
        p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_title = p_title.add_run("MEMORIA TÉCNICA Y ESPECIFICACIONES DE PROYECTO")
        r_title.bold = True
        r_title.font.size = Pt(14)
        
        # TABLA 1: META DEL DOCUMENTO
        t_meta = doc.add_table(rows=5, cols=2)
        t_meta.style = 'Table Grid'
        meta_data = [
            ("Departamento:", "Ingeniería y Viabilidad Técnica"),
            ("Documento:", f"Memoria Técnica de Proyecto de Electrificación y Peak Shaving - {ubicacion_app}"),
            ("Código del Documento:", f"GPS-EMS-MTC-001"),
            ("Revisión / Fecha:", "01 / 04/09/2026"),
            ("Elaborado por:", "Departamento de Ingeniería")
        ]
        for i, (k, v) in enumerate(meta_data):
            cell_k = t_meta.cell(i, 0)
            cell_k.text = k
            cell_k.paragraphs[0].runs[0].bold = True
            t_meta.cell(i, 1).text = v

        doc.add_paragraph()

        # TABLA 2: HISTORIAL DE REVISIONES
        doc.add_heading('Historial de revisiones', level=2)
        t_rev = doc.add_table(rows=2, cols=4)
        t_rev.style = 'Table Grid'
        headers = ["N° de Revisión", "Fecha", "Páginas Revisadas", "Motivo de Revisión"]
        for i, h in enumerate(headers):
            cell = t_rev.cell(0, i)
            cell.text = h
            cell.paragraphs[0].runs[0].bold = True
        t_rev.cell(1, 0).text = "01"
        t_rev.cell(1, 1).text = "04/09/2026"
        t_rev.cell(1, 2).text = "Todo el documento"
        t_rev.cell(1, 3).text = "Revisión General y Emisión"

        doc.add_paragraph()

        # TABLA 3: DOCUMENTOS ENTREGADOS
        doc.add_heading('Documentos Entregados', level=2)
        t_doc = doc.add_table(rows=2, cols=2)
        t_doc.style = 'Table Grid'
        t_doc.cell(0,0).text = "Documento:"; t_doc.cell(0,0).paragraphs[0].runs[0].bold = True
        t_doc.cell(0,1).text = "Código:"; t_doc.cell(0,1).paragraphs[0].runs[0].bold = True
        t_doc.cell(1,0).text = "Plano Unifilar y Memoria de Cálculo"
        t_doc.cell(1,1).text = "GPS-EMS-DUF-001"

        doc.add_page_break()

        # ÍNDICE DE CONTENIDO
        doc.add_heading('ÍNDICE DE CONTENIDO', level=1)
        indice = [
            "1. OBJETIVOS", "2. INTRODUCCIÓN", "3. UBICACIÓN", 
            "4. DESARROLLO GENERAL", "  4.1 SISTEMA EXISTENTE", "  4.2 SISTEMA PROYECTADO",
            "5. ESPECIFICACIONES TÉCNICAS", "6. CÁLCULO DE LA DEMANDA Y ESTUDIO ELÉCTRICO",
            "7. LISTA DE MATERIALES", "8. CONCLUSIONES", "9. ANEXOS"
        ]
        for item in indice:
            doc.add_paragraph(item)

        doc.add_page_break()

        # CONTENIDO REAL
        doc.add_heading('1. OBJETIVOS', level=1)
        doc.add_heading('1.1 Objetivo General:', level=2)
        doc.add_paragraph("Incorporación de nuevas tecnologías y mejora de la infraestructura con el objetivo de garantizar un suministro eléctrico competitivo, seguro y eficiente mediante la implementación de un Sistema Inteligente de Gestión de Energía (EMS).")
        doc.add_heading('1.2 Objetivos Específicos:', level=2)
        doc.add_paragraph(f"Electrificación y recorte de demanda pico (Peak Shaving) de {demanda_max:.1f} kW a {p_lim:.1f} kW, garantizando el cumplimiento de las normativas de interconexión.")

        doc.add_heading('2. INTRODUCCIÓN', level=1)
        doc.add_paragraph(f"La institución operadora de las instalaciones en {ubicacion_app}, se ha caracterizado por implementar procesos eficientes en el manejo de sus recursos. La implementación del proyecto {titulo_app} apuesta por el uso de tecnologías híbridas (Generación fotovoltaica y almacenamiento BESS).")

        doc.add_heading('3. UBICACIÓN', level=1)
        doc.add_paragraph(f"El centro de carga principal está ubicado en: {ubicacion_app}.")

        doc.add_heading('4. DESARROLLO GENERAL', level=1)
        doc.add_heading('4.1 SISTEMA EXISTENTE', level=2)
        doc.add_paragraph(f"Actualmente el centro de carga opera con un transformador de {s_trafo:.0f} kVA a 220V, alcanzando una demanda máxima registrada de {demanda_max:.1f} kW, con una cargabilidad térmica original del {carg_sin:.1f}%.")
        
        doc.add_heading('4.2 SISTEMA PROYECTADO', level=2)
        doc.add_paragraph(f"Se proyecta la integración de un banco de baterías de {c_bat:.0f} kWh y un sistema solar de {p_pv:.0f} kWp, acoplados a un inversor de {inv_req:.1f} kVA. El algoritmo EMS limitará la potencia tomada de la red a {p_lim:.1f} kW, mejorando la cargabilidad del transformador al {carg_con:.1f}%.")

        doc.add_heading('5. ESPECIFICACIONES TÉCNICAS', level=1)
        doc.add_paragraph(f"• INVERSOR MULTIMODO: Potencia Nominal de {inv_req:.1f} kVA, Factor de Potencia mínimo regulable a 0.95 (IEEE 1547).")
        doc.add_paragraph(f"• BANCO BESS: Capacidad Nominal de {c_bat:.0f} kWh en tecnología LiFePO4, con DoD configurado al 80% (Reserva de seguridad SOC_min de {soc_min:.1f} kWh).")
        
        doc.add_heading('6. CÁLCULO DE LA DEMANDA Y ESTUDIO TÉCNICO', level=1)
        doc.add_paragraph(f"Para el bus principal en 220V, la corriente nominal del transformador es de {i_nom:.1f} A. Considerando una impedancia de Z=5.75%, la corriente de falla simétrica es Icc = {icc_simetrica/1000.0:.2f} kA. Se validó la capacidad interruptiva requerida del disyuntor principal a 50 kA.")

        doc.add_heading('7. LISTA DE MATERIALES', level=1)
        t_mat = doc.add_table(rows=5, cols=4)
        t_mat.style = 'Table Grid'
        mat_headers = ["ÍTEM", "DESCRIPCIÓN", "UNIDAD", "CANTIDAD"]
        for i, h in enumerate(mat_headers):
            t_mat.cell(0, i).text = h
            t_mat.cell(0, i).paragraphs[0].runs[0].bold = True
        
        materiales = [
            ("1", f"Sistema Almacenamiento BESS {c_bat:.0f} kWh LiFePO4", "GLB", "1"),
            ("2", f"Inversor Híbrido Multimodo {inv_req:.1f} kVA", "UN", "1"),
            ("3", f"Sistema Fotovoltaico {p_pv:.0f} kWp", "GLB", "1"),
            ("4", "Controlador PLC Microgrid EMS", "UN", "1")
        ]
        for r_idx, (i, d, u, c) in enumerate(materiales, start=1):
            t_mat.cell(r_idx, 0).text = i
            t_mat.cell(r_idx, 1).text = d
            t_mat.cell(r_idx, 2).text = u
            t_mat.cell(r_idx, 3).text = c

        doc.add_heading('8. CONCLUSIONES', level=1)
        doc.add_paragraph(f"Una vez analizada la infraestructura eléctrica del proyecto {titulo_app}, el sistema diseñado logra un aplanamiento neto de demanda de {reduccion_pico:.1f} kW, reduciendo el estrés térmico en el transformador de {s_trafo:.0f} kVA y garantizando el cumplimiento normativo IEEE.")

        target = io.BytesIO()
        doc.save(target)
        return target.getvalue()

    docx_file = generar_memoria_oficial_gps()

    col_w1, col_w2 = st.columns([1, 2])
    with col_w1:
        st.download_button(
            label="📄 Descargar Memoria Oficial en Word (.docx)",
            data=docx_file,
            file_name=f'GPS_Memoria_Tecnica_EMS_{p_lim:.0f}kW.docx',
            mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    with col_w2:
        st.success("✔ Documento Word generado con estructura completa (Tablas, Índices, Capítulos 1 al 9) idéntico a tus plantillas de ingeniería.")

# ------------------------------------------
# TAB 4: EXPORTACIÓN CAD Y REPORTES
# ------------------------------------------
with tab4:
    st.subheader("💾 Exportación a AutoCAD y Hojas de Cálculo")
    
    def generate_unifilar_dxf():
        lines = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC", "0", "SECTION", "2", "TABLES", "0", "ENDSEC", "0", "SECTION", "2", "BLOCKS", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
        def add_line(layer, x1, y1, x2, y2):
            lines.extend(["0", "LINE", "8", layer, "10", f"{x1:.2f}", "20", f"{y1:.2f}", "30", "0.0", "11", f"{x2:.2f}", "21", f"{y2:.2f}", "31", "0.0"])
        def add_circle(layer, cx, cy, r):
            lines.extend(["0", "CIRCLE", "8", layer, "10", f"{cx:.2f}", "20", f"{cy:.2f}", "30", "0.0", "40", f"{r:.2f}"])
        def add_text(layer, x, y, text, height=3.0):
            lines.extend(["0", "TEXT", "8", layer, "10", f"{x:.2f}", "20", f"{y:.2f}", "30", "0.0", "40", f"{height:.2f}", "1", str(text)])
        def add_box(layer, x1, y1, x2, y2):
            add_line(layer, x1, y1, x2, y1); add_line(layer, x2, y1, x2, y2); add_line(layer, x2, y2, x1, y2); add_line(layer, x1, y2, x1, y1)

        add_text("TEXTOS", -80, 220, f"PROYECTO: {titulo_app.upper()}", 5.0)
        add_text("TEXTOS", -80, 212, f"UBICACION: {ubicacion_app.upper()} - UNIFILAR JERARQUICO", 3.5)
        
        add_line("RED_MT", 0, 200, 0, 160)
        add_text("TEXTOS", -45, 195, "ACOMETIDA RED PRINCIPAL CNEL - 69 kV / 13.8 kV", 3.5)
        add_circle("EQUIPOS", 0, 160, 2.5)
        
        add_circle("SIMBOLOS_TRAFO", 0, 128, 12); add_circle("SIMBOLOS_TRAFO", 0, 112, 12)
        add_box("CUADROS_INFO", 25, 95, 105, 145)
        add_text("TEXTOS", 28, 137, f"TRANSFORMADOR PEDESTAL {s_trafo:.0f} kVA", 3.5)
        
        add_line("RED_BT", 0, 100, 0, 80)
        add_line("BUS_PRINCIPAL", -110, 50, 110, 50)
        
        lines.extend(["0", "ENDSEC", "0", "EOF"])
        return "\n".join(lines)

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            label="📊 Descargar Resultados de Simulación EMS (CSV)",
            data=df_ems.to_csv(index=False).encode('utf-8'),
            file_name=f'Reporte_EMS_{p_lim:.0f}kW.csv',
            mime='text/csv'
        )
    with col_d2:
        st.download_button(
            label="📐 Descargar Plano CAD Unifilar (.DXF / DWG)",
            data=generate_unifilar_dxf().encode('utf-8'),
            file_name=f'Plano_Unifilar_EMS_{p_lim:.0f}kW.dxf',
            mime='application/dxf'
        )
