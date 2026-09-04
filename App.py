import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

# ==========================================
# CONFIGURACIÓN GENERAL DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Suite EMS - UPS Bloque D", layout="wide", page_icon="🛡️")

st.title("🛡️ Suite Módulos de Ingeniería Integrados - EMS Bloque D")
st.markdown("**Plataforma de Control Energético, Simulación Normativa y Gestión de Demanda**")
st.markdown("---")

# ==========================================
# BARRA LATERAL: CONFIGURACIÓN GLOBAL
# ==========================================
st.sidebar.header("⚙️ Parámetros Globales (EMS)")

limite_red = st.sidebar.number_input(
    "Set-point Límite de Red P_lim (kW)", 
    min_value=80.0, max_value=200.0, value=130.0, step=5.0
)
capacidad_bess = st.sidebar.number_input(
    "Capacidad Banco BESS C_bat (kWh)", 
    min_value=50.0, max_value=1000.0, value=250.0, step=10.0
)
potencia_pv = st.sidebar.number_input(
    "Potencia Fotovoltaica P_PV (kWp)", 
    min_value=0.0, max_value=300.0, value=150.0, step=10.0
)
carga_nocturna = st.sidebar.number_input(
    "Carga Nocturna BESS (kW)", 
    min_value=10.0, max_value=100.0, value=40.0, step=5.0
)

# ==========================================
# BASE DE DATOS Y ESTADO DE SIMULACIÓN
# ==========================================
if 'df_base' not in st.session_state:
    st.session_state.df_base = pd.DataFrame({
        'Hora': [f"{h:02d}:00" for h in range(24)],
        'P_Carga_(kW)': [36.0, 36.0, 36.0, 36.0, 36.0, 40.0, 60.0, 90.0, 120.0, 145.0, 160.0, 175.0, 179.1, 140.0, 150.0, 155.0, 160.0, 165.0, 172.0, 175.0, 130.0, 90.0, 50.0, 36.0],
        'P_PV_(kW)': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 5.0, 25.0, 55.0, 90.0, 120.0, 140.0, 150.0, 140.0, 120.0, 90.0, 55.0, 25.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    })

factor_escala_pv = potencia_pv / 150.0 if potencia_pv > 0 else 0.0
df_calc = st.session_state.df_base.copy()
df_calc['P_PV_(kW)'] = df_calc['P_PV_(kW)'] * factor_escala_pv

# ==========================================
# SELECCIÓN DE MÓDULOS DE INGENIERÍA
# ==========================================
modulos = [
    "📐 1. Diagrama Unifilar Jerárquico",
    "⚡ 2. Cálculo Normativo (IEEE 2030 / 1547)",
    "🏢 3. Distribución MT/BT & Concentración",
    "💥 4. Estudio de Cortocircuito (AIC)",
    "📄 5. Memoria Técnico-Descriptiva",
    "💾 6. Exportación CAD & Reportes"
]

modulo_seleccionado = st.radio("Seleccione el Módulo de Trabajo:", modulos, horizontal=True)
st.markdown("---")

# ==========================================
# ALGORITMO EMS DETERMINÍSTICO DE CÁLCULO
# ==========================================
df_calc['P_Red_Teorica'] = df_calc['P_Carga_(kW)'] - df_calc['P_PV_(kW)']

soc_min = 0.20 * capacidad_bess
soc_max = capacidad_bess
e_util = soc_max - soc_min
energia_actual = capacidad_bess * 0.50

p_bat_lista, p_red_real_lista, e_bat_lista, soc_lista = [], [], [], []

for idx, row in df_calc.iterrows():
    p_teorica = row['P_Red_Teorica']
    
    if p_teorica > limite_red:
        p_req = p_teorica - limite_red
        p_bat = p_req if (energia_actual - p_req) >= soc_min else max(0.0, energia_actual - soc_min)
    elif 1 <= idx <= 5:
        p_bat = -carga_nocturna if (energia_actual + carga_nocturna) <= soc_max else -(soc_max - energia_actual)
    else:
        p_bat = 0.0

    p_red_real = p_teorica - p_bat
    energia_actual -= p_bat
    soc_actual = (energia_actual / capacidad_bess) * 100.0

    p_bat_lista.append(round(p_bat, 2))
    p_red_real_lista.append(round(p_red_real, 2))
    e_bat_lista.append(round(energia_actual, 2))
    soc_lista.append(round(soc_actual, 2))

df_calc['P_Bateria_(kW)'] = p_bat_lista
df_calc['P_Red_Real_(kW)'] = p_red_real_lista
df_calc['Energia_Almacenada_(kWh)'] = e_bat_lista
df_calc['SOC_(%)'] = soc_lista

demanda_max = float(df_calc['P_Carga_(kW)'].max())
demanda_recortada = float(df_calc['P_Red_Real_(kW)'].max())
reduccion_pico = demanda_max - demanda_recortada
inv_req = potencia_pv / 0.95 if potencia_pv > 0 else (limite_red / 0.95)

v_linea = 220.0
s_trafo = 1000.0
z_percent = 5.75
i_nom = (s_trafo * 1000.0) / (1.73205 * v_linea)
icc_simetrica = i_nom / (z_percent / 100.0)
cargabilidad_sin = (demanda_max / s_trafo) * 100.0
cargabilidad_con = (demanda_recortada / s_trafo) * 100.0

# ==========================================
# GENERADOR DE PLANO CAD UNIFILAR (.DXF)
# ==========================================
def generate_unifilar_dxf(p_lim=130.0, c_bat=250.0, p_pv=150.0, s_trafo=1000.0):
    lines = []
    def add_line(layer, x1, y1, x2, y2):
        lines.extend(["0", "LINE", "8", layer, "10", f"{x1:.2f}", "20", f"{y1:.2f}", "30", "0.0", "11", f"{x2:.2f}", "21", f"{y2:.2f}", "31", "0.0"])

    def add_circle(layer, cx, cy, r):
        lines.extend(["0", "CIRCLE", "8", layer, "10", f"{cx:.2f}", "20", f"{cy:.2f}", "30", "0.0", "40", f"{r:.2f}"])

    def add_text(layer, x, y, text, height=3.0):
        lines.extend(["0", "TEXT", "8", layer, "10", f"{x:.2f}", "20", f"{y:.2f}", "30", "0.0", "40", f"{height:.2f}", "1", str(text)])

    def add_box(layer, x1, y1, x2, y2):
        add_line(layer, x1, y1, x2, y1)
        add_line(layer, x2, y1, x2, y2)
        add_line(layer, x2, y2, x1, y2)
        add_line(layer, x1, y2, x1, y1)

    lines.extend(["0", "SECTION", "2", "HEADER", "0", "ENDSEC"])
    lines.extend(["0", "SECTION", "2", "TABLES", "0", "ENDSEC"])
    lines.extend(["0", "SECTION", "2", "BLOCKS", "0", "ENDSEC"])
    lines.extend(["0", "SECTION", "2", "ENTITIES"])

    add_line("RED_MT", 0, 200, 0, 160)
    add_text("TEXTOS", -40, 205, "RED PRINCIPAL CNEL - MEDIA TENSION 69 kV / 13.8 kV", 4.0)
    
    add_circle("EQUIPOS", 0, 160, 2.5)
    add_text("TEXTOS", 8, 158, "CCF 100A + APARTARRAYOS 12 kV", 3.0)
    add_line("RED_MT", 0, 157.5, 0, 140)

    add_circle("SIMBOLOS_TRAFO", 0, 128, 12)
    add_circle("SIMBOLOS_TRAFO", 0, 112, 12)
    add_text("TEXTOS", -4, 125, "DELTA", 3.0)
    add_text("TEXTOS", -2, 109, "Y", 3.0)
    
    add_box("CUADROS_INFO", 25, 100, 95, 140)
    add_text("TEXTOS", 28, 132, f"TRANSFORMADOR {s_trafo:.0f} kVA", 3.5)
    add_text("TEXTOS", 28, 124, "Primario: 69 kV / 13.8 kV (Delta)", 2.5)
    add_text("TEXTOS", 28, 116, "Secundario: 220/127 V (3F-4H)", 2.5)
    add_text("TEXTOS", 28, 108, "Z% = 5.75%  |  OA  |  60 Hz", 2.5)

    add_line("RED_BT", 0, 100, 0, 80)
    add_box("EQUIPOS", -8, 65, 8, 80)
    add_text("TEXTOS", -5, 70, "ITM", 3.5)
    add_text("TEXTOS", 12, 70, "PRINCIPAL: 3P-2000 A (50 kA AIC @ 220V)", 3.0)

    add_line("RED_BT", 0, 65, 0, 50)
    add_line("BUS_PRINCIPAL", -100, 50, 100, 50)
    add_line("BUS_PRINCIPAL", -100, 49.5, 100, 49.5)
    add_text("TEXTOS", -80, 53, "TABLERO GENERAL DE DISTRIBUCION (TGBT) - 220/127 V (3F-4H)", 3.5)

    add_line("RED_BT", -70, 50, -70, 30)
    add_box("EQUIPOS", -75, 20, -65, 30)
    add_text("TEXTOS", -73, 23, "3P", 3.0)
    add_line("RED_BT", -70, 20, -70, 5)
    add_text("TEXTOS", -85, -2, "CARGAS BLOQUE D (179.1 kW Peak)", 2.5)

    add_line("RED_BT", 30, 50, 30, 30)
    add_box("EQUIPOS", 25, 20, 35, 30)
    add_text("TEXTOS", 27, 23, "3P", 3.0)
    add_line("RED_BT", 30, 20, 30, 5)
    
    add_box("EQUIPOS", 10, -15, 50, 5)
    add_text("TEXTOS", 14, -2, "INVERSOR HIBRIDO", 3.0)
    add_text("TEXTOS", 14, -8, f"S_nom: {p_pv/0.95:.1f} kVA", 2.5)
    add_text("TEXTOS", 14, -13, f"Set-point: {p_lim:.0f} kW", 2.5)

    add_line("RED_DC", 20, -15, 20, -30)
    add_line("RED_DC", 40, -15, 40, -30)

    add_box("EQUIPOS", 5, -45, 30, -30)
    add_text("TEXTOS", 8, -37, "ARREGLO PV", 2.5)
    add_text("TEXTOS", 8, -42, f"Capacidad: {p_pv:.0f} kWp", 2.5)

    add_box("EQUIPOS", 35, -45, 60, -30)
    add_text("TEXTOS", 38, -37, "BANCO BESS", 2.5)
    add_text("TEXTOS", 38, -42, f"Capacidad: {c_bat:.0f} kWh", 2.5)

    lines.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(lines)

# ==========================================
# GENERADOR VECTORIAL EN PANTALLA (PLOTLY)
# ==========================================
def build_plotly_sld(p_lim=130.0, c_bat=250.0, p_pv=150.0, s_trafo=1000.0):
    fig = go.Figure()
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    
    fig.add_trace(go.Scatter(x=[0, 0], y=[200, 160], mode='lines', line=dict(color='black', width=3), showlegend=False))
    fig.add_annotation(x=0, y=205, text="RED CNEL • MEDIA TENSIÓN 69 kV / 13.8 kV", showarrow=False, font=dict(size=13, color='blue', family='Arial Black'))
    
    fig.add_trace(go.Scatter(x=[0], y=[160], mode='markers', marker=dict(color='red', size=12), showlegend=False))
    fig.add_annotation(x=20, y=160, text="CCF 100A + APARTARRAYOS 12 kV", showarrow=False, font=dict(size=11))
    
    fig.add_shape(type="circle", x0=-12, y0=116, x1=12, y1=140, line_color="dodgerblue", line_width=3)
    fig.add_shape(type="circle", x0=-12, y0=100, x1=12, y1=124, line_color="dodgerblue", line_width=3)
    fig.add_annotation(x=0, y=128, text="Δ", showarrow=False, font=dict(size=14, color='black'))
    fig.add_annotation(x=0, y=112, text="Y", showarrow=False, font=dict(size=14, color='black'))
    
    fig.add_shape(type="rect", x0=25, y0=100, x1=95, y1=140, fillcolor="#eBF5FB", line_color="#3498DB", line_width=1.5)
    fig.add_annotation(x=60, y=132, text=f"TRANSFORMADOR {s_trafo:.0f} kVA", showarrow=False, font=dict(size=12, color='#1B4F72', family='Arial Black'))
    fig.add_annotation(x=60, y=122, text="Primario: 69 kV / 13.8 kV (Delta)", showarrow=False, font=dict(size=10))
    fig.add_annotation(x=60, y=114, text="Secundario: 220/127 V (3F-4H)", showarrow=False, font=dict(size=10))
    fig.add_annotation(x=60, y=106, text="Z% = 5.75%  |  OA  |  60 Hz", showarrow=False, font=dict(size=10))
    
    fig.add_trace(go.Scatter(x=[0, 0], y=[100, 80], mode='lines', line=dict(color='black', width=3), showlegend=False))
    fig.add_shape(type="rect", x0=-10, y0=65, x1=10, y1=80, fillcolor="white", line_color="black", line_width=2)
    fig.add_annotation(x=0, y=72.5, text="ITM", showarrow=False, font=dict(size=12, family='Arial Black'))
    fig.add_annotation(x=55, y=72.5, text="PRINCIPAL: 3P-2000 A (50 kA AIC @ 220V)", showarrow=False, font=dict(size=11, color='green', family='Arial Black'))
    
    fig.add_trace(go.Scatter(x=[0, 0], y=[65, 50], mode='lines', line=dict(color='black', width=3), showlegend=False))
    fig.add_trace(go.Scatter(x=[-100, 100], y=[50, 50], mode='lines', line=dict(color='#0073e6', width=6), showlegend=False))
    fig.add_annotation(x=0, y=56, text="TABLERO GENERAL DE DISTRIBUCIÓN (TGBT) • 220/127 V (3F-4H)", showarrow=False, font=dict(size=12, family='Arial Black'))
    
    fig.add_trace(go.Scatter(x=[-60, -60], y=[50, 30], mode='lines', line=dict(color='black', width=2), showlegend=False))
    fig.add_shape(type="rect", x0=-66, y0=20, x1=-54, y1=30, fillcolor="white", line_color="black", line_width=1.5)
    fig.add_annotation(x=-60, y=25, text="3P", showarrow=False, font=dict(size=10))
    fig.add_trace(go.Scatter(x=[-60, -60], y=[20, 5], mode='lines', line=dict(color='red', width=2), showlegend=False))
    fig.add_annotation(x=-60, y=-2, text="CARGAS BLOQUE D<br>(179.1 kW Peak)", showarrow=False, font=dict(size=10, color='red'))
    
    fig.add_trace(go.Scatter(x=[60, 60], y=[50, 30], mode='lines', line=dict(color='black', width=2), showlegend=False))
    fig.add_shape(type="rect", x0=54, y0=20, x1=66, y1=30, fillcolor="white", line_color="black", line_width=1.5)
    fig.add_annotation(x=60, y=25, text="3P", showarrow=False, font=dict(size=10))
    fig.add_trace(go.Scatter(x=[60, 60], y=[20, 5], mode='lines', line=dict(color='purple', width=2), showlegend=False))
    
    fig.add_shape(type="rect", x0=35, y0=-15, x1=85, y1=5, fillcolor="#F4ECF7", line_color="#884EA0", line_width=2)
    fig.add_annotation(x=60, y=-1, text="INVERSOR HÍBRIDO", showarrow=False, font=dict(size=11, color='#512E5F', family='Arial Black'))
    fig.add_annotation(x=60, y=-7, text=f"S_nom: {p_pv/0.95:.1f} kVA", showarrow=False, font=dict(size=10))
    fig.add_annotation(x=60, y=-12, text=f"Set-point: {p_lim:.0f} kW", showarrow=False, font=dict(size=10))
    
    fig.add_trace(go.Scatter(x=[45, 45], y=[-15, -30], mode='lines', line=dict(color='orange', width=2), showlegend=False))
    fig.add_trace(go.Scatter(x=[75, 75], y=[-15, -30], mode='lines', line=dict(color='green', width=2), showlegend=False))
    
    fig.add_shape(type="rect", x0=32, y0=-45, x1=58, y1=-30, fillcolor="#FEF9E7", line_color="#F1C40F", line_width=1.5)
    fig.add_annotation(x=45, y=-35, text="ARREGLO PV", showarrow=False, font=dict(size=10, family='Arial Black'))
    fig.add_annotation(x=45, y=-41, text=f"{p_pv:.0f} kWp", showarrow=False, font=dict(size=10))
    
    fig.add_shape(type="rect", x0=62, y0=-45, x1=88, y1=-30, fillcolor="#E8F8F5", line_color="#2ECC71", line_width=1.5)
    fig.add_annotation(x=75, y=-35, text="BANCO BESS", showarrow=False, font=dict(size=10, family='Arial Black'))
    fig.add_annotation(x=75, y=-41, text=f"{c_bat:.0f} kWh", showarrow=False, font=dict(size=10))

    fig.update_layout(height=600, margin=dict(l=10, r=10, t=10, b=10), template='plotly_white')
    return fig

# ==========================================
# MÓDULO 1: DIAGRAMA UNIFILAR JERÁRQUICO
# ==========================================
if modulo_seleccionado == "📐 1. Diagrama Unifilar Jerárquico":
    st.subheader("📐 Módulo 1: Diagrama Unifilar Jerárquico Interactiva y Exportable CAD")
    st.markdown("Generación vectorial en tiempo real del esquema unifilar del Bloque D con simbología estandarizada e interconexión BESS/PV.")
    
    # Renderizado en pantalla del Unifilar
    fig_sld = build_plotly_sld(limite_red, capacidad_bess, potencia_pv, s_trafo)
    st.plotly_chart(fig_sld, use_container_width=True)
    
    # Exportación a AutoCAD .DXF
    dxf_content = generate_unifilar_dxf(limite_red, capacidad_bess, potencia_pv, s_trafo)
    
    col_cad1, col_cad2 = st.columns([1, 2])
    with col_cad1:
        st.download_button(
            label="📐 Descargar Plano CAD Unifilar (.DXF / DWG)",
            data=dxf_content.encode('utf-8'),
            file_name=f'Plano_Unifilar_EMS_{limite_red:.0f}kW.dxf',
            mime='application/dxf'
        )
    with col_cad2:
        st.success("✔ Archivo vectorial DXF generado en capas nativas (`RED_MT`, `RED_BT`, `EQUIPOS`, `TEXTOS`, `BUS_PRINCIPAL`). Se abre directamente en AutoCAD y se guarda como .dwg")

elif modulo_seleccionado == "⚡ 2. Cálculo Normativo (IEEE 2030 / 1547)":
    st.subheader("⚡ Módulo 2: Cálculo Normativo Internacional (IEEE Std 2030.2 / 2030.7 / 1547)")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Reserva Mínima SOC_min (IEEE 2030.2)", f"{soc_min:.1f} kWh", "20% Capacidad")
    col_b.metric("Capacidad Útil BESS E_util", f"{e_util:.1f} kWh", "DoD Max: 80%")
    col_c.metric("Potencia Aparente Inversor S_inv (IEEE 1547)", f"{inv_req:.1f} kVA", "FP = 0.95")
    st.dataframe(df_calc.style.format(precision=1), use_container_width=True)

elif modulo_seleccionado == "🏢 3. Distribución MT/BT & Concentración":
    st.subheader("🏢 Módulo 3: Modelado de Transformador Pedestal y Concentración de Cargas")
    c1, c2, c3 = st.columns(3)
    c1.metric("Capacidad Trafo Bloque D", "1000 kVA")
    c2.metric("Cargabilidad Original", f"{cargabilidad_sin:.1f}%", f"Pico: {demanda_max:.1f} kW")
    c3.metric("Cargabilidad con EMS", f"{cargabilidad_con:.1f}%", f"Pico: {demanda_recortada:.1f} kW", delta_color="normal")
    st.success("✔ El transformador de 1000 kVA opera holgadamente dentro del rango térmico de seguridad.")

elif modulo_seleccionado == "💥 4. Estudio de Cortocircuito (AIC)":
    st.subheader("💥 Módulo 4: Estudio de Cortocircuito y Capacidad Interruptiva (AIC)")
    m1, m2, m3 = st.columns(3)
    m1.metric("Corriente Nominal In (220V)", f"{i_nom:.1f} A")
    m2.metric("Corriente Falla Simétrica Icc", f"{icc_simetrica / 1000.0:.2f} kA")
    m3.metric("Capacidad Interruptiva Mínima", "50 kA", "Validez Art. 110-9")

elif modulo_seleccionado == "📄 5. Memoria Técnico-Descriptiva":
    st.subheader("📄 Módulo 5: Memoria Técnica y Especificaciones de Proyecto (Formato Oficial GPS Group)")
    
    # Generación Word
    from docx import Document
    def generar_memoria_completa_gps_docx():
        doc = Document()
        for section in doc.sections:
            section.top_margin = Inches(1)
            section.bottom_margin = Inches(1)
            section.left_margin = Inches(1)
            section.right_margin = Inches(1)
            
        p_top = doc.add_paragraph()
        p_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_top = p_top.add_run("MEMORIA TÉCNICA Y ESPECIFICACIONES DE PROYECTO")
        r_top.bold = True
        r_top.font.size = Pt(14)

        table_hdr = doc.add_table(rows=4, cols=2)
        table_hdr.alignment = WD_TABLE_ALIGNMENT.CENTER
        table_hdr.style = 'Table Grid'
        
        hdr_data = [
            ("Departamento:", "Ingeniería y Viabilidad Técnica"),
            ("Documento:", "Memoria Técnica y Especificaciones de Proyecto EMS - Peak Shaving UPS Bloque D"),
            ("Código del Documento:", "GPS-EMS-UPSD-MTC-001"),
            ("Revisión / Fecha:", "Rev. C / 04/09/2026")
        ]
        for idx, (lbl, val) in enumerate(hdr_data):
            row = table_hdr.rows[idx]
            row.cells[0].paragraphs[0].add_run(lbl).bold = True
            row.cells[1].paragraphs[0].add_run(val)

        doc.add_paragraph()
        doc.add_heading('1. OBJETIVOS:', level=1)
        doc.add_paragraph(f"Diseñar y validar el Sistema EMS para el Bloque D limitando la red a {limite_red:.0f} kW con un BESS de {capacidad_bess:.0f} kWh y PV de {potencia_pv:.0f} kWp.")
        
        doc.add_heading('2. ANTECEDENTES:', level=1)
        doc.add_paragraph(f"Acometida alimentada por transformador de 1000 kVA (69 kV / 0.22 kV), registrando picos de demanda bruta de hasta {demanda_max:.1f} kW.")
        
        doc.add_heading('3. BASE TÉCNICA:', level=1)
        doc.add_paragraph("IEEE Std 2030.2-2015, IEEE Std 2030.7-2017, IEEE Std 1547-2018, NEC Art. 110-9.")
        
        doc.add_heading('4. DESARROLLO Y CÁLCULOS:', level=1)
        doc.add_paragraph(f"• Reducción de pico: {demanda_max:.1f} kW -> {limite_red:.1f} kW (Aplanamiento de {reduccion_pico:.1f} kW).")
        doc.add_paragraph(f"• Cortocircuito: Icc = {icc_simetrica/1000.0:.2f} kA (Protección requerida 50 kA AIC).")
        doc.add_paragraph(f"• Cargabilidad Trafo: Reducida de {cargabilidad_sin:.1f}% a {cargabilidad_con:.1f}%.")

        target = io.BytesIO()
        doc.save(target)
        return target.getvalue()

    docx_bytes = generar_memoria_completa_gps_docx()
    st.download_button(
        label="📄 Descargar Memoria Técnica Oficial en Word (.docx)",
        data=docx_bytes,
        file_name=f'GPS-EMS-UPSD-MTC-001_MEMORIA_TECNICA_UPS.docx',
        mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

elif modulo_seleccionado == "💾 6. Exportación CAD & Reportes":
    st.subheader("💾 Módulo 6: Exportación de Expediente Ejecutivo y Reportes")
    csv_bytes = df_calc.to_csv(index=False).encode('utf-8')
    dxf_content = generate_unifilar_dxf(limite_red, capacidad_bess, potencia_pv, s_trafo)
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.download_button(
            label="⬇️ Descargar Reporte de Resultados (CSV)",
            data=csv_bytes,
            file_name=f'Reporte_EMS_{limite_red:.0f}kW.csv',
            mime='text/csv'
        )
    with col_d2:
        st.download_button(
            label="📐 Descargar Plano CAD Unifilar (.DXF / DWG)",
            data=dxf_content.encode('utf-8'),
            file_name=f'Plano_Unifilar_EMS_{limite_red:.0f}kW.dxf',
            mime='application/dxf'
        )
