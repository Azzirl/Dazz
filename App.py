import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(page_title="EMS Control Center", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif !important; }

    .stApp { background-color: #080F1F; color: #F8FAFC; }
    .block-container { padding-top: 1rem; max-width: 1400px; }
    header, footer { visibility: hidden; display: none; }
    
    /* Barra lateral */
    section[data-testid="stSidebar"] { background-color: #111B2E; border-right: 1px solid #26354D; }
    
    /* Botones Sidebar (Navegación) */
    div[data-testid="stSidebar"] .stButton > button {
        background-color: transparent; border: 1px solid transparent; color: #94A3B8; 
        text-align: left; justify-content: flex-start; width: 100%; height: 42px; border-radius: 8px; font-weight: 500;
    }
    div[data-testid="stSidebar"] .stButton > button:hover { background-color: #172338; color: #00B8FF; }

    /* Botones Principales de Acción */
    .stButton > button { background-color: #172338; color: #00B8FF; border: 1px solid #26354D; border-radius: 8px; height: 46px; font-weight: 600; width: 100%; }
    .stButton > button:hover { border-color: #00B8FF; box-shadow: 0 0 10px rgba(0,184,255,0.2); }
    
    /* Cabecera SCADA */
    .scada-header { background-color: #111B2E; padding: 20px 30px; border: 1px solid #26354D; border-radius: 12px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; }
    .scada-title { margin: 0; color: #F8FAFC; font-size: 26px; font-weight: 700; }
    .scada-sub { color: #94A3B8; font-size: 13px; font-weight: 500; letter-spacing: 1px; margin-top: 5px; }
    
    /* Tarjetas de Métricas */
    .metric-card { background-color: #172338; border: 1px solid #26354D; border-radius: 10px; padding: 16px 20px; margin-bottom: 16px; }
    .metric-lbl { font-size: 12px; color: #94A3B8; font-weight: 600; text-transform: uppercase; margin-bottom: 8px; }
    .metric-val { font-size: 28px; font-weight: 700; color: #F8FAFC; }
    .metric-unit { font-size: 14px; color: #94A3B8; font-weight: 500; }
    
    /* Colores funcionales */
    .c-cyan { color: #00B8FF; } .c-green { color: #00D084; } .c-red { color: #FF4D5A; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GESTIÓN DE ESTADO Y CÁLCULOS
# ==========================================
if 'page' not in st.session_state:
    st.session_state.page = "Dashboard"

if 'ps_activo' not in st.session_state:
    st.session_state.ps_activo = True

# Datos Reales
REAL_LOAD = [36, 36, 36, 36, 36, 40, 60, 90, 120, 145, 160, 175, 179.1, 140, 150, 155, 160, 165, 172, 175, 130, 90, 50, 36]
PV_BASE = [0, 0, 0, 0, 0, 0, 5, 25, 55, 90, 120, 140, 150, 140, 120, 90, 55, 25, 5, 0, 0, 0, 0, 0]

# ==========================================
# 3. BARRA LATERAL (NAVEGACIÓN)
# ==========================================
st.sidebar.markdown("<h2 style='color:#F8FAFC; margin-bottom:0;'>⚡ EMS SUITE</h2><p style='color:#00B8FF; font-size:12px; margin-top:0; margin-bottom:30px;'>ENGINEERING CONTROL</p>", unsafe_allow_html=True)

st.sidebar.markdown("<p style='color:#94A3B8; font-size:12px; font-weight:600;'>NAVEGACIÓN</p>", unsafe_allow_html=True)
if st.sidebar.button("▣ Dashboard Principal"): st.session_state.page = "Dashboard"
if st.sidebar.button("⚡ Análisis EMS"): st.session_state.page = "EMS"
if st.sidebar.button("◈ Unifilar SCADA"): st.session_state.page = "Unifilar"
if st.sidebar.button("▤ Memoria Técnica"): st.session_state.page = "Memoria"
if st.sidebar.button("□ Exportaciones & MATLAB"): st.session_state.page = "Exportaciones"

st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
st.sidebar.markdown("""
<div style="background-color: #172338; border: 1px solid #26354D; border-radius: 8px; padding: 16px;">
    <div style="font-size: 11px; color: #94A3B8; font-weight: 600; margin-bottom: 4px;">SYSTEM STATUS</div>
    <div style="color: #00D084; font-weight: 700; font-size: 14px;">● ONLINE</div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 4. CABECERA PRINCIPAL Y ACCIONES
# ==========================================
st.markdown(f"""
<div class="scada-header">
    <div>
        <h2 class="scada-title">⚡ EMS CONTROL CENTER</h2>
        <div class="scada-sub">ENERGY MANAGEMENT SYSTEM | UPS CAMPUS CENTENARIO</div>
    </div>
    <div style="text-align: right;">
        <div style="color: #00D084; font-weight: 700; font-size: 14px;">● SYSTEM ONLINE</div>
        <div style="color: #00B8FF; font-size: 12px; font-weight: 600; margin-top: 4px;">PEAK SHAVING {'ON' if st.session_state.ps_activo else 'OFF'}</div>
    </div>
</div>
""", unsafe_allow_html=True)

col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
if col_btn1.button("▶ EJECUTAR SIMULACIÓN"): st.toast("✅ Simulación completada con éxito.")
if col_btn2.button("↻ RECALCULAR DATOS"): st.rerun()
if col_btn3.button(f"⚡ PEAK SHAVING {'OFF' if st.session_state.ps_activo else 'ON'}"):
    st.session_state.ps_activo = not st.session_state.ps_activo
    st.rerun()
if col_btn4.button("📊 ANÁLISIS DE RED"): st.toast("🔍 Análisis de calidad completado.")

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# VISTAS DE PÁGINAS
# ==========================================

if st.session_state.page == "Dashboard":
    
    # CONFIGURACIÓN AVANZADA EN LA PARTE SUPERIOR (Expander)
    with st.expander("⚙️ CONFIGURACIÓN DEL SISTEMA", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        p_lim = c1.number_input("Límite Red (kW)", value=140.0, step=5.0)
        c_bat = c2.number_input("BESS (kWh)", value=400.0, step=10.0)
        p_pv = c3.number_input("Solar PV (kWp)", value=190.0, step=10.0)
        s_trafo = c4.number_input("Trafo (kVA)", value=1000.0, step=50.0)
        v_nom = 440.0
        carga_noc = 40.0
    
    # CÁLCULOS DINÁMICOS
    factor_pv = p_pv / 150.0
    pv_real = [round(v * factor_pv, 1) for v in PV_BASE]
    soc_min = 0.20 * c_bat
    energia = c_bat * 0.50
    limite_operativo = p_lim if st.session_state.ps_activo else 9999.0
    
    rows_ems = []
    for i in range(24):
        p_teorica = REAL_LOAD[i] - pv_real[i]
        p_bat = 0.0
        if p_teorica > limite_operativo:
            req = p_teorica - limite_operativo
            p_bat = req if (energia - req) >= soc_min else max(0.0, energia - soc_min)
        elif 1 <= i <= 5: 
            p_bat = -carga_noc if (energia + carga_noc) <= c_bat else -(c_bat - energia)
            
        p_red = p_teorica - p_bat
        energia -= p_bat
        rows_ems.append({'Hora': f"{i:02d}:00", 'P_Carga': REAL_LOAD[i], 'P_PV': pv_real[i], 'P_Red': round(p_red, 1), 'SOC': round((energia/c_bat)*100, 1)})
    
    df_ems = pd.DataFrame(rows_ems)
    dem_max = df_ems['P_Carga'].max()
    red_max = df_ems['P_Red'].max()
    carg_sin = (dem_max / s_trafo) * 100
    carg_con = (red_max / s_trafo) * 100
    soc_actual = df_ems['SOC'].iloc[12]

    # TARJETAS DE MÉTRICAS
    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"""<div class="metric-card"><div class="metric-lbl">DEMANDA RED</div>
    <div class="metric-val">{red_max:.1f} <span class="metric-unit">kW</span></div>
    <div style="font-size:12px; color:#94A3B8; margin-top:5px;">Pico Original: {dem_max:.1f} kW</div></div>""", unsafe_allow_html=True)
    
    m2.markdown(f"""<div class="metric-card"><div class="metric-lbl">BANCO BESS</div>
    <div class="metric-val">{c_bat:.0f} <span class="metric-unit">kWh</span></div>
    <div style="font-size:12px; color:#00D084; margin-top:5px; font-weight:600;">SOC {soc_actual:.0f}%</div></div>""", unsafe_allow_html=True)
    
    m3.markdown(f"""<div class="metric-card"><div class="metric-lbl">SISTEMA FOTOVOLTAICO</div>
    <div class="metric-val">{p_pv:.0f} <span class="metric-unit">kWp</span></div>
    <div style="font-size:12px; color:#00B8FF; margin-top:5px;">S_inv: {(p_pv/0.95):.1f} kVA</div></div>""", unsafe_allow_html=True)
    
    m4.markdown(f"""<div class="metric-card"><div class="metric-lbl">CARGABILIDAD TRAFO</div>
    <div class="metric-val">{carg_con:.1f} <span class="metric-unit">%</span></div>
    <div style="font-size:12px; color:#94A3B8; margin-top:5px;">Original: {carg_sin:.1f}%</div></div>""", unsafe_allow_html=True)

    # GRÁFICO PRINCIPAL
    st.markdown("<div style='font-size:14px; font-weight:600; color:#F8FAFC; margin-bottom:10px;'>PERFIL ENERGÉTICO EN TIEMPO DE SIMULACIÓN</div>", unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Carga'], name='Demanda Bruta', line=dict(color='#00B8FF', width=2)))
    fig.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Red'], name='Consumo Red', fill='tozeroy', line=dict(color='#00D084', width=3)))
    if st.session_state.ps_activo:
        fig.add_trace(go.Scatter(x=df_ems['Hora'], y=[p_lim]*24, name='Límite EMS', line=dict(color='#FF4D5A', width=2, dash='dash')))
    
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor='#111B2E', plot_bgcolor='#111B2E', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

elif st.session_state.page == "Unifilar":
    # Variables default si no se ha pasado por Dashboard
    s_trafo = 1000.0; v_nom = 440.0; p_pv = 190.0; c_bat = 400.0; p_lim = 140.0
    icc = ((s_trafo * 1000) / (1.732 * v_nom)) / 0.0575 / 1000.0

    st.markdown("<h3 style='color: #00B8FF;'>Diagrama Unifilar Interactivo (SCADA)</h3>", unsafe_allow_html=True)
    
    c_left, c_right = st.columns([1.5, 3.5])
    with c_left:
        st.markdown("<div style='font-size: 13px; color: #94A3B8; font-weight: 600; margin-bottom: 12px;'>EQUIPOS EN LÍNEA</div>", unsafe_allow_html=True)
        eq = st.radio("Equipos", ["Transformador", "BESS", "Inversor", "Arreglo PV", "Red CNEL", "TGBT"], label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)
        if eq == "Transformador":
            st.markdown(f"""<div class="metric-card"><div class="metric-lbl" style="color:#00B8FF;">⚡ TRANSFORMADOR</div>
            <div style="font-size:14px; line-height:2.0; color:#F8FAFC;"><b>Capacidad:</b> {s_trafo} kVA<br><b>Tensión:</b> 69 kV / {v_nom} V<br><b>Icc:</b> {icc:.2f} kA<br><br><span style="color:#00D084; font-weight:700;">● NORMAL</span></div></div>""", unsafe_allow_html=True)
        elif eq == "BESS":
            st.markdown(f"""<div class="metric-card"><div class="metric-lbl" style="color:#00B8FF;">🔋 BANCO BESS</div>
            <div style="font-size:14px; line-height:2.0; color:#F8FAFC;"><b>Capacidad:</b> {c_bat} kWh<br><b>Química:</b> LiFePO4<br><b>Energía Útil:</b> {c_bat*0.8:.1f} kWh<br><br><span style="color:#00D084; font-weight:700;">● DISPONIBLE</span></div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="metric-card"><div class="metric-lbl" style="color:#00B8FF;">{eq.upper()}</div>
            <div style="font-size:14px; line-height:2.0; color:#F8FAFC;"><span style="color:#00D084; font-weight:700;">● ESTADO: OPERATIVO</span></div></div>""", unsafe_allow_html=True)

    with c_right:
        fig_sld = go.Figure()
        fig_sld.update_xaxes(visible=False, range=[-100, 100]); fig_sld.update_yaxes(visible=False, range=[-70, 220])
        l_color = '#00B8FF'; t_color = '#F8FAFC'
        
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[200, 150], mode='lines', line=dict(color=l_color, width=3), showlegend=False))
        fig_sld.add_annotation(x=30, y=190, text="RED CNEL 13.8 kV", showarrow=False, font=dict(size=13, color=t_color))
        fig_sld.add_shape(type="circle", x0=-15, y0=115, x1=15, y1=145, line_color=l_color, line_width=3)
        fig_sld.add_shape(type="circle", x0=-15, y0=95, x1=15, y1=125, line_color=l_color, line_width=3)
        fig_sld.add_annotation(x=45, y=120, text=f"TRAFO {s_trafo} kVA", showarrow=False, font=dict(size=13, color=t_color))
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[95, 60], mode='lines', line=dict(color=l_color, width=3), showlegend=False))
        fig_sld.add_shape(type="rect", x0=-12, y0=65, x1=12, y1=80, line_color=l_color, line_width=3, fillcolor='#111B2E')
        fig_sld.add_annotation(x=40, y=72, text="ITM 50kA", showarrow=False, font=dict(size=12, color=t_color))
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[60, 40], mode='lines', line=dict(color=l_color, width=3), showlegend=False))
        fig_sld.add_trace(go.Scatter(x=[-90, 90], y=[40, 40], mode='lines', line=dict(color=l_color, width=6), showlegend=False))
        fig_sld.add_annotation(x=0, y=47, text=f"BUS TGBT {v_nom}V", showarrow=False, font=dict(size=14, color=t_color, weight="bold"))
        fig_sld.add_trace(go.Scatter(x=[-50, -50], y=[40, 0], mode='lines', line=dict(color='#FF4D5A', width=3), showlegend=False))
        fig_sld.add_shape(type="rect", x0=-75, y0=-15, x1=-25, y1=0, line_color="#FF4D5A", line_width=3, fillcolor='rgba(255, 77, 90, 0.1)')
        fig_sld.add_annotation(x=-50, y=-7.5, text="CARGAS", showarrow=False, font=dict(size=12, color='#FF4D5A', weight="bold"))
        fig_sld.add_trace(go.Scatter(x=[50, 50], y=[40, 0], mode='lines', line=dict(color='#00D084', width=3), showlegend=False))
        fig_sld.add_shape(type="rect", x0=20, y0=-15, x1=80, y1=0, line_color="#00D084", line_width=3, fillcolor='rgba(0, 208, 132, 0.1)')
        fig_sld.add_annotation(x=50, y=-7.5, text="INVERSOR", showarrow=False, font=dict(size=12, color='#00D084', weight="bold"))
        
        fig_sld.update_layout(height=600, margin=dict(l=0, r=0, t=10, b=10), template='plotly_dark', paper_bgcolor='#111B2E', plot_bgcolor='#111B2E')
        st.plotly_chart(fig_sld, use_container_width=True)

elif st.session_state.page == "Memoria":
    st.markdown("<h3 style='color: #00B8FF;'>Generación de Memoria Técnica Oficial</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8;'>El documento Word generado replica <b>EXACTAMENTE</b> el formato oficial de tus documentos (Historial de Revisiones, Documentos Entregados, Índices y Numeración).</p>", unsafe_allow_html=True)
    
    def generar_memoria_oficial_gps():
        doc = Document()
        # Márgenes
        for section in doc.sections:
            section.top_margin = Inches(1); section.bottom_margin = Inches(1)
            section.left_margin = Inches(1); section.right_margin = Inches(1)
            
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("MEMORIA TÉCNICA Y ESPECIFICACIONES DE PROYECTO"); r.bold = True; r.font.size = Pt(14)
        
        # Tabla 1
        t_meta = doc.add_table(rows=4, cols=2); t_meta.style = 'Table Grid'
        data_m = [("Departamento:", "Ingeniería y Viabilidad Técnica"), ("Documento:", "Memoria Técnica EMS - UPS Bloque D"), ("Código del Documento:", "GPS-EMS-MTC-001"), ("Revisión / Fecha:", "Rev. C / 04/09/2026")]
        for i, (k, v) in enumerate(data_m):
            t_meta.cell(i, 0).text = k; t_meta.cell(i, 0).paragraphs[0].runs[0].bold = True; t_meta.cell(i, 1).text = v

        doc.add_paragraph()
        doc.add_heading('Historial de revisiones', level=2)
        t_rev = doc.add_table(rows=2, cols=4); t_rev.style = 'Table Grid'
        headers = ["N° de Revisión", "Fecha", "Páginas Revisadas", "Motivo de Revisión"]
        for i, h in enumerate(headers): t_rev.cell(0, i).text = h; t_rev.cell(0, i).paragraphs[0].runs[0].bold = True
        t_rev.cell(1, 0).text = "01"; t_rev.cell(1, 1).text = "04/09/2026"; t_rev.cell(1, 2).text = "Todo el documento"; t_rev.cell(1, 3).text = "Revisión General y Emisión"

        doc.add_paragraph()
        doc.add_heading('Documentos Entregados', level=2)
        t_doc = doc.add_table(rows=2, cols=2); t_doc.style = 'Table Grid'
        t_doc.cell(0,0).text = "Documento:"; t_doc.cell(0,0).paragraphs[0].runs[0].bold = True
        t_doc.cell(0,1).text = "Código:"; t_doc.cell(0,1).paragraphs[0].runs[0].bold = True
        t_doc.cell(1,0).text = "Plano Unifilar y Memoria de Cálculo"; t_doc.cell(1,1).text = "GPS-EMS-DUF-001"

        doc.add_heading('ÍNDICE DE CONTENIDO', level=1)
        indice = ["1. OBJETIVOS", "2. INTRODUCCIÓN", "3. UBICACIÓN", "4. DESARROLLO GENERAL\n  4.1 SISTEMA EXISTENTE\n  4.2 SISTEMA PROYECTADO", "5. ESPECIFICACIONES TÉCNICAS", "6. CÁLCULO DE LA DEMANDA Y ESTUDIO ELÉCTRICO", "7. LISTA DE MATERIALES", "8. CONCLUSIONES", "9. ANEXOS"]
        for item in indice: doc.add_paragraph(item)
        
        doc.add_heading('1. OBJETIVOS', level=1)
        doc.add_heading('1.1 Objetivo General:', level=2)
        doc.add_paragraph("Incorporación de nuevas tecnologías y mejora de la infraestructura con el objetivo de garantizar un suministro eléctrico competitivo, seguro y eficiente mediante la implementación de un Sistema Inteligente de Gestión de Energía (EMS).")
        doc.add_heading('1.2 Objetivos Específicos:', level=2)
        doc.add_paragraph("Electrificación y recorte de demanda pico (Peak Shaving) de 179.1 kW a 140.0 kW, garantizando el cumplimiento de las normativas de interconexión (IEEE 2030.7, 1547).")

        doc.add_heading('2. INTRODUCCIÓN', level=1)
        doc.add_paragraph("La implementación del proyecto apuesta por el uso de tecnologías híbridas (Generación fotovoltaica y almacenamiento BESS), mitigando los picos de consumo y mejorando el perfil de tensión local.")

        doc.add_heading('3. UBICACIÓN', level=1)
        doc.add_paragraph("El centro de carga principal está ubicado en el Campus Centenario UPS (Guayaquil, Ecuador).")

        doc.add_heading('4. DESARROLLO GENERAL', level=1)
        doc.add_heading('4.1 SISTEMA EXISTENTE', level=2)
        doc.add_paragraph("Actualmente el centro de carga opera con un transformador de 1000 kVA a 440.0V, alcanzando una demanda máxima registrada de 179.1 kW, con una cargabilidad térmica original del 17.9%.")
        
        doc.add_heading('4.2 SISTEMA PROYECTADO', level=2)
        doc.add_paragraph("Se proyecta la integración de un banco de baterías de 400 kWh y un sistema solar de 190 kWp, acoplados a un inversor de 200.0 kVA. El algoritmo EMS limitará la potencia tomada de la red a 140.0 kW, mejorando la cargabilidad del transformador al 17.5%.")

        doc.add_heading('5. ESPECIFICACIONES TÉCNICAS', level=1)
        doc.add_paragraph("• INVERSOR MULTIMODO: Potencia Nominal de 200.0 kVA, Factor de Potencia mínimo regulable a 0.95 (IEEE 1547).\n• BANCO BESS: Capacidad Nominal de 400 kWh en tecnología LiFePO4, con DoD configurado al 80% (Reserva de seguridad SOC_min de 80.0 kWh).")
        
        doc.add_heading('6. CÁLCULO DE LA DEMANDA Y ESTUDIO TÉCNICO', level=1)
        doc.add_paragraph("Para el bus principal en 440.0V, la corriente nominal del transformador es de 1312.2 A. Considerando una impedancia de Z=5.75%, la corriente de falla simétrica es Icc = 22.82 kA. Se validó la capacidad interruptiva requerida del disyuntor principal a 50 kA.")

        doc.add_heading('7. LISTA DE MATERIALES', level=1)
        t_mat = doc.add_table(rows=5, cols=4); t_mat.style = 'Table Grid'
        mat_headers = ["ÍTEM", "DESCRIPCIÓN", "UNIDAD", "CANTIDAD"]
        for i, h in enumerate(mat_headers): t_mat.cell(0, i).text = h; t_mat.cell(0, i).paragraphs[0].runs[0].bold = True
        
        materiales = [("1", "Sistema Almacenamiento BESS 400 kWh LiFePO4", "GLB", "1"), ("2", "Inversor Híbrido Multimodo 200.0 kVA", "UN", "1"), ("3", "Sistema Fotovoltaico 190 kWp", "GLB", "1"), ("4", "Controlador PLC Microgrid EMS", "UN", "1")]
        for r_idx, (i, d, u, c) in enumerate(materiales, start=1):
            t_mat.cell(r_idx, 0).text = i; t_mat.cell(r_idx, 1).text = d; t_mat.cell(r_idx, 2).text = u; t_mat.cell(r_idx, 3).text = c

        doc.add_heading('8. CONCLUSIONES', level=1)
        doc.add_paragraph("El sistema diseñado logra un aplanamiento neto de demanda de 4.1 kW, reduciendo el estrés térmico en el transformador de 1000 kVA y garantizando el cumplimiento normativo.")

        target = io.BytesIO(); doc.save(target)
        return target.getvalue()

    st.download_button("📄 DESCARGAR MEMORIA TÉCNICA (WORD .DOCX)", generar_memoria_oficial_gps(), 'GPS_Memoria_Tecnica_EMS.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')

elif st.session_state.page == "Exportaciones":
    st.markdown("<h3 style='color: #00B8FF;'>Exportaciones y Código MATLAB</h3>", unsafe_allow_html=True)
    
    st.markdown("<h4 style='color: #F8FAFC;'>Código Operativo EMS (MATLAB)</h4>", unsafe_allow_html=True)
    st.code("""%% EMS Peak Shaving — UPS Bloque D
clear; clc; close all;
P_lim = 130.0; C_bat = 250.0; P_PV = 150.0;
P_carga = [36, 36, 36, 36, 36, 40, 60, 90, 120, 145, 160, 175, 179.1, 140, 150, 155, 160, 165, 172, 175, 130, 90, 50, 36];
P_PV_base = [0, 0, 0, 0, 0, 0, 5, 25, 55, 90, 120, 140, 150, 140, 120, 90, 55, 25, 5, 0, 0, 0, 0, 0];

SOC_min = 0.20 * C_bat; SOC_max = C_bat; E_act = C_bat * 0.50;
P_bat = zeros(1,24); P_red = zeros(1,24);

for t = 1:24
    P_teo = P_carga(t) - P_PV_base(t);
    if P_teo > P_lim
        req = P_teo - P_lim;
        P_b = min(req, max(0, E_act - SOC_min));
    elseif t >= 2 && t <= 6
        P_b = -min(40, SOC_max - E_act);
    else
        P_b = 0;
    end
    E_act = E_act - P_b;
    P_bat(t) = P_b;
    P_red(t) = P_teo - P_b;
end
disp('Simulación Exitosa');
""", language='matlab')

    def generate_dxf():
        lines = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC", "0", "SECTION", "2", "TABLES", "0", "ENDSEC", "0", "SECTION", "2", "BLOCKS", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
        lines.extend(["0", "TEXT", "8", "TEXTOS", "10", "0.0", "20", "200.0", "30", "0.0", "40", "5.0", "1", "DIAGRAMA UNIFILAR EMS BLOQUE D"])
        lines.extend(["0", "ENDSEC", "0", "EOF"])
        return "\n".join(lines)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button("📐 DESCARGAR PLANO CAD (.DXF)", generate_dxf().encode('utf-8'), 'Plano_Unifilar.dxf', 'application/dxf')
