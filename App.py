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
# CONFIGURACIÓN DE PÁGINA EN STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Suite EMS - UPS Bloque D",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para Dashboard de Grado Industrial
st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    
    .card-metric {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .metric-title { font-size: 13px; color: #64748b; font-weight: 500; margin-bottom: 4px; }
    .metric-value { font-size: 26px; font-weight: 700; color: #0f172a; }
    .metric-unit { font-size: 13px; font-weight: 400; color: #64748b; margin-left: 4px; }
    .metric-sub { font-size: 11px; color: #94a3b8; font-weight: 500; margin-top: 4px; }
    
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-blue { background-color: #dbeafe; color: #1e40af; }
    .badge-green { background-color: #d1fae5; color: #065f46; }
    .badge-slate { background-color: #f1f5f9; color: #334155; }
    
    .alert-box {
        background-color: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 8px;
        padding: 14px 18px;
        color: #991b1b;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATOS MEDIDOS REALES (METREL MI2792 - AGOSTO 2022)
# ==========================================
REAL_LOAD = [36, 36, 36, 36, 36, 40, 60, 90, 120, 145, 160, 175, 179.1, 140, 150, 155, 160, 165, 172, 175, 130, 90, 50, 36]
PV_BASE = [0, 0, 0, 0, 0, 0, 5, 25, 55, 90, 120, 140, 150, 140, 120, 90, 55, 25, 5, 0, 0, 0, 0, 0]
IRRADIANCE_GYE = [1.2, 1.4, 1.8, 2.5, 3.2, 3.8, 4.1, 4.3, 4.2, 3.9, 3.2, 2.1, 1.8, 1.5, 1.2, 0.9, 0.5, 0.2, 0, 0, 0, 0, 0, 0]

# ==========================================
# BARRA LATERAL: PARÁMETROS OPERATIVOS
# ==========================================
st.sidebar.header("⚙️ Control de Parámetros EMS")

p_lim = st.sidebar.slider("Set-point límite de red P_lim (kW)", min_value=80.0, max_value=200.0, value=130.0, step=5.0)
c_bat = st.sidebar.slider("Capacidad BESS C_bat (kWh)", min_value=50.0, max_value=600.0, value=250.0, step=10.0)
p_pv = st.sidebar.slider("Potencia FV instalada P_PV (kWp)", min_value=0.0, max_value=300.0, value=150.0, step=10.0)
carga_noc = st.sidebar.slider("Carga nocturna BESS (kW)", min_value=10.0, max_value=100.0, value=40.0, step=5.0)

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Red y Transformador")
v_nom = st.sidebar.number_input("Tensión nominal BT (V)", value=220.0, step=10.0)
s_trafo = st.sidebar.number_input("Potencia Trafo Pedestal (kVA)", value=1000.0, step=50.0)

# ==========================================
# CÁLCULOS DEL EMS EN PYTHON
# ==========================================
factor_pv = p_pv / 150.0 if p_pv > 0 else 0.0
pv_real = [round(v * factor_pv, 1) for v in PV_BASE]

soc_min = 0.20 * c_bat
soc_max = c_bat
e_util = c_bat * 0.80
energia = c_bat * 0.50

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
        'Hora': f"{i:02d}:00",
        'P_Carga_(kW)': REAL_LOAD[i],
        'P_PV_(kW)': pv_real[i],
        'P_Bateria_(kW)': round(p_bat, 1),
        'P_Red_Real_(kW)': round(p_red, 1),
        'Energia_BESS_(kWh)': round(energia, 1),
        'SOC_(%)': round(soc, 1)
    })

df_ems = pd.DataFrame(rows_ems)

demanda_max = float(df_ems['P_Carga_(kW)'].max())
demanda_recortada = float(df_ems['P_Red_Real_(kW)'].max())
reduccion_pico = demanda_max - demanda_recortada
inv_req = p_pv / 0.95 if p_pv > 0 else p_lim / 0.95

i_nom = (s_trafo * 1000.0) / (1.73205 * v_nom)
icc_simetrica = i_nom / (5.75 / 100.0)
cargabilidad_sin = (demanda_max / s_trafo) * 100.0
cargabilidad_con = (demanda_recortada / s_trafo) * 100.0

# ==========================================
# HEADER PRINCIPAL
# ==========================================
st.markdown(f"""
<div style="background-color: #ffffff; padding: 18px 24px; border-radius: 10px; border: 1px solid #e2e8f0; margin-bottom: 20px;">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <h2 style="margin: 0; color: #0f172a; font-size: 22px;">⚡ Suite EMS — Gestor de Gestión Energética Bloque D (UPS)</h2>
            <p style="margin: 4px 0 0 0; color: #64748b; font-size: 13px;">Optimización por Peak Shaving · Reducción de Demanda de Red · Cumplimiento IEEE 2030.7 / 1547</p>
        </div>
        <div>
            <span class="status-badge badge-blue">UPS Campus Centenario</span>
            <span class="status-badge badge-green">Trafo {s_trafo:.0f} kVA</span>
            <span class="status-badge badge-slate">P_lim = {p_lim:.0f} kW</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# NAVEGACIÓN POR MÓDULOS DE INGENIERÍA
# ==========================================
tab_list = [
    "⚙️ Configuración & Control",
    "📐 Diagrama Unifilar",
    "⚡ EMS & Peak Shaving",
    "📊 Calidad de Energía",
    "☀️ Dimensionamiento FV+BESS",
    "🔄 Comparador Real vs Sim",
    "📄 Memoria Técnica",
    "💻 Código MATLAB / ETAP"
]

tabs = st.tabs(tab_list)

# ------------------------------------------
# MÓDULO 1: CONFIGURACIÓN & CONTROL
# ------------------------------------------
with tabs[0]:
    st.subheader("⚙️ Panel de Control y Métricas Clave del EMS")
    st.markdown("Ajusta las variables en el panel lateral para simular distintos escenarios en tiempo real.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="card-metric">
            <div class="metric-title">Reducción Neta de Demanda Pico</div>
            <div class="metric-value" style="color:#059669;">{reduccion_pico:.1f} <span class="metric-unit">kW</span></div>
            <div class="metric-sub">Pico original: {demanda_max:.1f} kW → Recortado: {demanda_recortada:.1f} kW</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="card-metric">
            <div class="metric-title">Corriente de Cortocircuito Icc</div>
            <div class="metric-value">{icc_simetrica/1000.0:.2f} <span class="metric-unit">kA</span></div>
            <div class="metric-sub">Cálculo simétrico en bus {v_nom:.0f}V (%Z=5.75%)</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="card-metric">
            <div class="metric-title">Cargabilidad del Transformador</div>
            <div class="metric-value">{cargabilidad_con:.1f} <span class="metric-unit">%</span></div>
            <div class="metric-sub">Sin EMS: {cargabilidad_sin:.1f}% de capacidad térmica</div>
        </div>
        """, unsafe_allow_html=True)

# ------------------------------------------
# MÓDULO 2: DIAGRAMA UNIFILAR JERÁRQUICO
# ------------------------------------------
with tabs[1]:
    st.subheader("📐 Diagrama Unifilar Jerárquico de Interconexión")
    st.markdown("Esquema vectorial generado según normativas **IEEE 2030.7** e **IEEE 1547**:")
    
    # Construcción de gráfica Plotly del Unifilar
    fig_sld = go.Figure()
    fig_sld.update_xaxes(visible=False)
    fig_sld.update_yaxes(visible=False)
    
    # Línea MT
    fig_sld.add_trace(go.Scatter(x=[0, 0], y=[200, 160], mode='lines', line=dict(color='#1e293b', width=3), showlegend=False))
    fig_sld.add_annotation(x=0, y=205, text="ACOMETIDA RED PRINCIPAL CNEL • 69 kV / 13.8 kV (3F-3H, 60 Hz)", showarrow=False, font=dict(size=12, color='#1e40af', family='Arial Black'))
    
    # Protecciones CCF
    fig_sld.add_trace(go.Scatter(x=[0], y=[160], mode='markers', marker=dict(color='#dc2626', size=12), showlegend=False))
    fig_sld.add_annotation(x=22, y=160, text="CCF 100A + APARTARRAYOS 12 kV", showarrow=False, font=dict(size=11))
    
    # Círculos Trafo
    fig_sld.add_shape(type="circle", x0=-12, y0=116, x1=12, y1=140, line_color="#0284c7", line_width=3)
    fig_sld.add_shape(type="circle", x0=-12, y0=100, x1=12, y1=124, line_color="#0284c7", line_width=3)
    fig_sld.add_annotation(x=0, y=128, text="Δ", showarrow=False, font=dict(size=14, color='black'))
    fig_sld.add_annotation(x=0, y=112, text="Y", showarrow=False, font=dict(size=14, color='black'))
    
    # Caja Info Trafo
    fig_sld.add_shape(type="rect", x0=25, y0=95, x1=100, y1=145, fillcolor="#f0f9ff", line_color="#0284c7", line_width=1.5)
    fig_sld.add_annotation(x=62, y=137, text=f"TRANSFORMADOR PEDESTAL {s_trafo:.0f} kVA", showarrow=False, font=dict(size=11, color='#0369a1', family='Arial Black'))
    fig_sld.add_annotation(x=62, y=127, text="Primario: 69 kV / 13.8 kV (Delta)", showarrow=False, font=dict(size=9.5))
    fig_sld.add_annotation(x=62, y=118, text=f"Secundario: {v_nom:.0f}/127 V (3F-4H, Dyn11)", showarrow=False, font=dict(size=9.5))
    fig_sld.add_annotation(x=62, y=109, text=f"Z% = 5.75%  |  In_sec = {i_nom:.1f} A", showarrow=False, font=dict(size=9.5))
    fig_sld.add_annotation(x=62, y=101, text=f"Icc_sim = {icc_simetrica/1000.0:.2f} kA  |  OA / 60 Hz", showarrow=False, font=dict(size=9.5, color='#991b1b'))
    
    # ITM
    fig_sld.add_trace(go.Scatter(x=[0, 0], y=[100, 80], mode='lines', line=dict(color='#1e293b', width=3), showlegend=False))
    fig_sld.add_shape(type="rect", x0=-10, y0=65, x1=10, y1=80, fillcolor="white", line_color="#1e293b", line_width=2)
    fig_sld.add_annotation(x=0, y=72.5, text="ITM", showarrow=False, font=dict(size=12, family='Arial Black'))
    fig_sld.add_annotation(x=68, y=72.5, text="DISYUNTOR PRINCIPAL TGBT: 3P-2000 A (50 kA AIC @ 220V)", showarrow=False, font=dict(size=11, color='#15803d', family='Arial Black'))
    
    # Bus Principal
    fig_sld.add_trace(go.Scatter(x=[0, 0], y=[65, 50], mode='lines', line=dict(color='#1e293b', width=3), showlegend=False))
    fig_sld.add_trace(go.Scatter(x=[-110, 110], y=[50, 50], mode='lines', line=dict(color='#2563eb', width=6), showlegend=False))
    fig_sld.add_annotation(x=0, y=56, text=f"TABLERO GENERAL DE DISTRIBUCIÓN (TGBT) • BUS {v_nom:.0f}/127V · 3F-4H", showarrow=False, font=dict(size=11, family='Arial Black'))
    
    # Rama Cargas
    fig_sld.add_trace(go.Scatter(x=[-60, -60], y=[50, 30], mode='lines', line=dict(color='#1e293b', width=2), showlegend=False))
    fig_sld.add_shape(type="rect", x0=-66, y0=20, x1=-54, y1=30, fillcolor="white", line_color="#1e293b", line_width=1.5)
    fig_sld.add_annotation(x=-60, y=25, text="3P", showarrow=False, font=dict(size=10))
    fig_sld.add_trace(go.Scatter(x=[-60, -60], y=[20, 5], mode='lines', line=dict(color='#ef4444', width=2), showlegend=False))
    
    fig_sld.add_shape(type="rect", x0=-85, y0=-15, x1=-35, y1=5, fillcolor="#fef2f2", line_color="#ef4444", line_width=1.5)
    fig_sld.add_annotation(x=-60, y=-1, text="CARGAS BLOQUE D (UPS)", showarrow=False, font=dict(size=10, color='#991b1b', family='Arial Black'))
    fig_sld.add_annotation(x=-60, y=-7, text=f"Demanda Pico: {demanda_max:.1f} kW", showarrow=False, font=dict(size=9.5))
    fig_sld.add_annotation(x=-60, y=-12, text="Carga Base: 36.0 kW", showarrow=False, font=dict(size=9.5))

    # Rama Inversor
    fig_sld.add_trace(go.Scatter(x=[60, 60], y=[50, 30], mode='lines', line=dict(color='#1e293b', width=2), showlegend=False))
    fig_sld.add_shape(type="rect", x0=54, y0=20, x1=66, y1=30, fillcolor="white", line_color="#1e293b", line_width=1.5)
    fig_sld.add_annotation(x=60, y=25, text="3P", showarrow=False, font=dict(size=10))
    fig_sld.add_trace(go.Scatter(x=[60, 60], y=[20, 5], mode='lines', line=dict(color='#8b5cf6', width=2), showlegend=False))
    
    fig_sld.add_shape(type="rect", x0=32, y0=-20, x1=88, y1=5, fillcolor="#faf5ff", line_color="#a855f7", line_width=2)
    fig_sld.add_annotation(x=60, y=-1, text="INVERSOR HÍBRIDO MULTIMODO", showarrow=False, font=dict(size=11, color='#6b21a8', family='Arial Black'))
    fig_sld.add_annotation(x=60, y=-7, text=f"S_nom: {inv_req:.1f} kVA (FP = 0.95)", showarrow=False, font=dict(size=9.5))
    fig_sld.add_annotation(x=60, y=-13, text=f"Control EMS Set-point: {p_lim:.0f} kW", showarrow=False, font=dict(size=9.5, color='#6b21a8', family='Arial Black'))
    
    # PV + BESS
    fig_sld.add_trace(go.Scatter(x=[45, 45], y=[-20, -35], mode='lines', line=dict(color='#f97316', width=2), showlegend=False))
    fig_sld.add_trace(go.Scatter(x=[75, 75], y=[-20, -35], mode='lines', line=dict(color='#10b981', width=2), showlegend=False))
    
    fig_sld.add_shape(type="rect", x0=30, y0=-55, x1=58, y1=-35, fillcolor="#fefce8", line_color="#eab308", line_width=1.5)
    fig_sld.add_annotation(x=44, y=-41, text="ARREGLO PV", showarrow=False, font=dict(size=10, family='Arial Black'))
    fig_sld.add_annotation(x=44, y=-47, text=f"{potencia_pv:.0f} kWp", showarrow=False, font=dict(size=9.5))
    fig_sld.add_annotation(x=44, y=-52, text="Módulos PERC 550W", showarrow=False, font=dict(size=8.5))
    
    fig_sld.add_shape(type="rect", x0=62, y0=-55, x1=92, y1=-35, fillcolor="#ecfdf5", line_color="#10b981", line_width=1.5)
    fig_sld.add_annotation(x=77, y=-41, text="BANCO BESS LiFePO4", showarrow=False, font=dict(size=10, family='Arial Black'))
    fig_sld.add_annotation(x=77, y=-47, text=f"{capacidad_bess:.0f} kWh (512V DC)", showarrow=False, font=dict(size=9.5))
    fig_sld.add_annotation(x=77, y=-52, text=f"E_util: {e_util:.0f} kWh (DoD 80%)", showarrow=False, font=dict(size=8.5))

    fig_sld.update_layout(height=580, margin=dict(l=10, r=10, t=10, b=10), template='plotly_white')
    st.plotly_chart(fig_sld, use_container_width=True)
    
    # Generador de archivo DXF
    def generate_unifilar_dxf():
        lines = []
        def add_line(layer, x1, y1, x2, y2):
            lines.extend(["0", "LINE", "8", layer, "10", f"{x1:.2f}", "20", f"{y1:.2f}", "30", "0.0", "11", f"{x2:.2f}", "21", f"{y2:.2f}", "31", "0.0"])
        def add_circle(layer, cx, cy, r):
            lines.extend(["0", "CIRCLE", "8", layer, "10", f"{cx:.2f}", "20", f"{cy:.2f}", "30", "0.0", "40", f"{r:.2f}"])
        def add_text(layer, x, y, text, height=3.0):
            lines.extend(["0", "TEXT", "8", layer, "10", f"{x:.2f}", "20", f"{y:.2f}", "30", "0.0", "40", f"{height:.2f}", "1", str(text)])
        def add_box(layer, x1, y1, x2, y2):
            add_line(layer, x1, y1, x2, y1); add_line(layer, x2, y1, x2, y2); add_line(layer, x2, y2, x1, y2); add_line(layer, x1, y2, x1, y1)

        lines.extend(["0", "SECTION", "2", "HEADER", "0", "ENDSEC", "0", "SECTION", "2", "TABLES", "0", "ENDSEC", "0", "SECTION", "2", "BLOCKS", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"])
        add_text("TEXTOS", -80, 220, "PROYECTO: SISTEMA EMS PEAK SHAVING - UPS BLOQUE D", 5.0)
        add_line("RED_MT", 0, 200, 0, 160)
        add_text("TEXTOS", -45, 195, "ACOMETIDA RED PRINCIPAL CNEL - 69 kV / 13.8 kV (3F-3H, 60 Hz)", 3.5)
        add_circle("EQUIPOS", 0, 160, 2.5)
        add_circle("SIMBOLOS_TRAFO", 0, 128, 12); add_circle("SIMBOLOS_TRAFO", 0, 112, 12)
        add_box("CUADROS_INFO", 25, 95, 105, 145)
        add_text("TEXTOS", 28, 137, f"TRANSFORMADOR PEDESTAL {s_trafo:.0f} kVA", 3.5)
        add_line("RED_BT", 0, 100, 0, 80)
        add_line("BUS_PRINCIPAL", -110, 50, 110, 50)
        lines.extend(["0", "ENDSEC", "0", "EOF"])
        return "\n".join(lines)

    dxf_data = generate_unifilar_dxf()
    col_cad1, col_cad2 = st.columns([1, 2])
    with col_cad1:
        st.download_button(
            label="📐 Descargar Plano CAD Unifilar (.DXF / DWG)",
            data=dxf_data.encode('utf-8'),
            file_name=f'Plano_Unifilar_EMS_{p_lim:.0f}kW.dxf',
            mime='application/dxf'
        )
    with col_cad2:
        st.success("✔ Archivo vectorial DXF generado en capas nativas para AutoCAD.")

# ------------------------------------------
# MÓDULO 3: EMS & PEAK SHAVING
# ------------------------------------------
with tabs[2]:
    st.subheader("⚡ Despacho Energético y Recorte de Picos (24 Horas)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Demanda Pico Bruta Original", f"{demanda_max:.1f} kW")
    col2.metric("Demanda Máxima Red c/EMS", f"{demanda_recortada:.1f} kW", delta=f"-{reduccion_pico:.1f} kW", delta_color="normal")
    col3.metric("Porcentaje de Recorte", f"{(reduccion_pico/demanda_max)*100.0:.1f} %")

    # Gráfico de Perfiles de Potencia
    fig_ems = go.Figure()
    fig_ems.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Carga_(kW)'], name='Demanda Bruta (kW)', line=dict(color='#2563eb', width=2.5)))
    fig_ems.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_PV_(kW)'], name='Generación PV (kW)', line=dict(color='#f59e0b', width=2)))
    fig_ems.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Red_Real_(kW)'], name='Potencia Red c/EMS (kW)', fill='tozeroy', line=dict(color='#ef4444', width=2.5)))
    fig_ems.add_trace(go.Scatter(x=df_ems['Hora'], y=[p_lim]*24, name=f'Límite Set-point ({p_lim:.0f} kW)', line=dict(color='#10b981', width=2, dash='dash')))
    fig_ems.update_layout(title="Perfiles de Potencia Activa (24 Horas)", xaxis_title="Hora del Día", yaxis_title="Potencia (kW)", template="plotly_white", height=380)
    st.plotly_chart(fig_ems, use_container_width=True)

    # Gráfico de SOC BESS
    fig_soc = go.Figure()
    fig_soc.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['SOC_(%)'], name='SOC BESS (%)', line=dict(color='#0d9488', width=2.5), fill='tozeroy'))
    fig_soc.update_layout(title="Estado de Carga del Banco BESS (SOC %)", xaxis_title="Hora del Día", yaxis_title="SOC (%)", template="plotly_white", height=240, yaxis=dict(range=[0, 105]))
    st.plotly_chart(fig_soc, use_container_width=True)

    # Tabla 24 Horas
    st.markdown("### Tabla de Balance Energético Horario")
    st.dataframe(df_ems, use_container_width=True)

# ------------------------------------------
# MÓDULO 4: CALIDAD DE ENERGÍA
# ------------------------------------------
with tabs[3]:
    st.subheader("📊 Análisis de Calidad de Energía (Medidor METREL MI2792)")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("THD Tensión Máximo", "2.2 %", "Cumple < 8% EN 50160")
    col2.metric("Flicker Plt Máximo", "1.12", "NO CUMPLE > 1.0", delta_color="inverse")
    col3.metric("Factor de Potencia Mínimo", "0.63", "Nocturno sin carga")

    st.markdown("""
    <div class="alert-box">
        <b>⚠️ Inconformidad Detectada: Flicker (Plt > 1.0)</b><br/>
        Las mediciones de campo registran variaciones rápidas de tensión que superan los límites permitidos. El inversor híbrido del BESS compensará potencia reactiva de forma dinámica (IEEE 1547) para estabilizar el voltaje del nodo.
    </div>
    """, unsafe_allow_html=True)

# ------------------------------------------
# MÓDULO 5: DIMENSIONAMIENTO FV + BESS
# ------------------------------------------
with tabs[4]:
    st.subheader("☀️ Dimensionamiento del Generador Fotovoltaico y BESS")
    
    num_mod = int((p_pv * 1000) / 550) if p_pv > 0 else 0
    area_mod = num_mod * 2.2
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Módulos PV Requeridos", f"{num_mod} uds.", "PERC 550 Wp")
    col2.metric("Área Necesaria en Techo", f"{area_mod:.0f} m²")
    col3.metric("Capacidad Inversor Híbrido", f"{inv_req:.1f} kVA", "FP = 0.95")

    fig_irr = go.Figure()
    fig_irr.add_trace(go.Scatter(x=df_ems['Hora'], y=IRRADIANCE_GYE, name='Irradiación (kW/m²)', line=dict(color='#f59e0b', width=2.5), fill='tozeroy'))
    fig_irr.update_layout(title="Perfil de Irradiación Solar Típico en Guayaquil (HPS = 4.3 h/día)", xaxis_title="Hora", yaxis_title="kW/m²", template="plotly_white", height=280)
    st.plotly_chart(fig_irr, use_container_width=True)

# ------------------------------------------
# MÓDULO 6: COMPARADOR REAL VS SIMULACIÓN
# ------------------------------------------
with tabs[5]:
    st.subheader("🔄 Comparación: Perfil Medido vs Simulación EMS")
    
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Scatter(x=df_ems['Hora'], y=REAL_LOAD, name='Demanda Real Medida (kW)', line=dict(color='#2563eb', width=2.5)))
    fig_comp.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Red_Real_(kW)'], name='Demanda Gestionada EMS (kW)', line=dict(color='#10b981', width=2.5)))
    fig_comp.update_layout(title="Aplanamiento de la Curva de Demanda", xaxis_title="Hora", yaxis_title="Potencia (kW)", template="plotly_white", height=360)
    st.plotly_chart(fig_comp, use_container_width=True)

# ------------------------------------------
# MÓDULO 7: MEMORIA TÉCNICA (DOCX)
# ------------------------------------------
with tabs[6]:
    st.subheader("📄 Generación de Memoria Técnica Oficial (Formato Word)")
    st.markdown("Descargue la Memoria Técnica en formato Word (`.docx`) estructurada según las normas de control de documentos de **GPS Group / CNEL EP**:")

    def generar_memoria_docx():
        doc = Document()
        for section in doc.sections:
            section.top_margin = Inches(1); section.bottom_margin = Inches(1)
            section.left_margin = Inches(1); section.right_margin = Inches(1)
            
        p_top = doc.add_paragraph()
        p_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_top = p_top.add_run("MEMORIA TÉCNICA Y ESPECIFICACIONES DE PROYECTO")
        r_top.bold = True; r_top.font.size = Pt(14)

        table_hdr = doc.add_table(rows=4, cols=2)
        table_hdr.alignment = WD_TABLE_ALIGNMENT.CENTER; table_hdr.style = 'Table Grid'
        
        hdr_data = [
            ("Departamento:", "Ingeniería y Viabilidad Técnica"),
            ("Documento:", "Memoria Técnica EMS - Peak Shaving UPS Bloque D"),
            ("Código del Documento:", "GPS-EMS-UPSD-MTC-001"),
            ("Revisión / Fecha:", "Rev. C / 04/09/2026")
        ]
        for idx, (lbl, val) in enumerate(hdr_data):
            row = table_hdr.rows[idx]
            row.cells[0].paragraphs[0].add_run(lbl).bold = True
            row.cells[1].paragraphs[0].add_run(val)

        doc.add_paragraph()
        doc.add_heading('1. OBJETIVOS:', level=1)
        doc.add_paragraph(f"Implementar el sistema EMS para recortar la demanda pico del Bloque D a {p_lim:.0f} kW con BESS de {c_bat:.0f} kWh y PV de {p_pv:.0f} kWp.")
        
        doc.add_heading('2. RESULTADOS OPERATIVOS:', level=1)
        doc.add_paragraph(f"• Demanda Pico Original: {demanda_max:.1f} kW")
        doc.add_paragraph(f"• Demanda Recortada con EMS: {demanda_recortada:.1f} kW")
        doc.add_paragraph(f"• Reducción de Pico: {reduccion_pico:.1f} kW ({(reduccion_pico/demanda_max)*100.0:.1f}%)")
        doc.add_paragraph(f"• Corriente de Cortocircuito Icc: {icc_simetrica/1000.0:.2f} kA (Protección requerida 50 kA AIC)")

        target = io.BytesIO()
        doc.save(target)
        return target.getvalue()

    docx_file = generar_memoria_docx()
    st.download_button(
        label="📄 Descargar Memoria Técnica Completa en Word (.docx)",
        data=docx_file,
        file_name='GPS-EMS-UPSD-MTC-001_MEMORIA_TECNICA.docx',
        mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

# ------------------------------------------
# MÓDULO 8: CÓDIGO MATLAB / ETAP
# ------------------------------------------
with tabs[7]:
    st.subheader("💻 Código Autogenerado para MATLAB y ETAP")
    
    tab_mat, tab_etap = st.tabs(["Script MATLAB (.m)", "Guía Modelado ETAP"])
    
    with tab_mat:
        matlab_code = f"""%% ============================================================
%% EMS Peak Shaving — UPS Bloque D
%% Generado para Tesis de Maestría
%% ============================================================
clear; clc; close all;

P_lim    = {p_lim};       % Límite red [kW]
C_bat    = {c_bat};      % Capacidad BESS [kWh]
P_PV     = {p_pv};       % Potencia PV instalada [kWp]
V_nom    = {v_nom};        % Tensión nominal BT [V]
S_trafo  = {s_trafo};    % Potencia trafo [kVA]

P_carga = [{', '.join(map(str, REAL_LOAD))}];
P_PV_base = [{', '.join(map(str, PV_BASE))}];

factor_PV = P_PV / 150;
P_PV_real = P_PV_base * factor_PV;

SOC_min = 0.20 * C_bat;
SOC_max = C_bat;
E_act   = C_bat * 0.50;

P_bat = zeros(1,24);
P_red = zeros(1,24);

for t = 1:24
    P_teo = P_carga(t) - P_PV_real(t);
    if P_teo > P_lim
        req = P_teo - P_lim;
        P_b = min(req, max(0, E_act - SOC_min));
    elseif t >= 2 && t <= 6
        P_b = -min({carga_noc}, SOC_max - E_act);
    else
        P_b = 0;
    end
    E_act = E_act - P_b;
    P_bat(t) = P_b;
    P_red(t) = P_teo - P_b;
end

disp('=== SIMULACIÓN COMPLETADA ===');
fprintf('Demanda pico recortada: %.1f kW\\n', max(P_red));
"""
        st.code(matlab_code, language='matlab')
        
    with tab_etap:
        st.markdown(f"""
        ### Guía para Modelado en ETAP
        1. **Red Principal:** 13.8 kV, Fuente infinita 500 MVA SCC.
        2. **Transformador:** {s_trafo:.0f} kVA, 13.8 kV / {v_nom/1000:.3f} kV, Dyn11, %Z = 5.75%.
        3. **Estudio Short Circuit:** $I_{{cc}}$ simulada = **{icc_simetrica/1000.0:.2f} kA**.
        4. **Protección Principal:** Disyuntor 3P 2000A con capacidad interruptiva de **50 kA AIC**.
        """)
