import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(page_title="EMS Control Center", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

# ==========================================
# 2. ESTILOS CSS AVANZADOS (SCADA DARK THEME & TEXT FIX)
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #0b1121; color: #f8fafc; }
    .block-container { padding-top: 1rem; max-width: 1400px; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* Textos nítidos en modo oscuro */
    section[data-testid="stSidebar"] { background-color: #0f172a; border-right: 1px solid #1e293b; }
    section[data-testid="stSidebar"] * { color: #f8fafc !important; font-weight: 500; }
    .stMarkdown p, .stText p, .stRadio p, .stSlider label, .stTextInput label, .stSelectbox label {
        color: #e2e8f0 !important; font-weight: 600 !important; font-size: 14px !important;
    }
    div[data-testid="stThumbValue"] { color: #ffffff !important; font-weight: bold !important; }
    
    /* Cabecera del Centro de Control */
    .scada-header {
        display: flex; justify-content: space-between; align-items: center; 
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        padding: 15px 25px; border-bottom: 2px solid #0ea5e9; border-radius: 8px; margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
    }
    .scada-title { margin: 0; color: #f8fafc !important; font-size: 24px; font-weight: 800; letter-spacing: 1px; }
    .scada-subtitle { color: #94a3b8 !important; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 2px; }
    .blinking { animation: blinker 1.5s cubic-bezier(.5, 0, 1, 1) infinite alternate; color: #10b981 !important; font-weight: 700; font-size: 14px; text-shadow: 0 0 8px #10b981; }
    @keyframes blinker { 50% { opacity: 0.3; } }
    
    /* Tarjetas de Métricas SCADA */
    .scada-card {
        background-color: #1e293b; border: 1px solid #334155; border-top: 3px solid #0ea5e9;
        border-radius: 6px; padding: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s;
    }
    .scada-card:hover { transform: translateY(-2px); border-color: #0ea5e9; }
    .scada-label { font-size: 12px; color: #94a3b8 !important; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
    .scada-value { font-size: 28px; font-weight: 700; color: #38bdf8 !important; margin:0; padding:0;}
    .scada-unit { font-size: 14px; color: #cbd5e1 !important; font-weight: 500; margin-left: 4px; }
    .scada-sub { font-size: 12px; margin-top: 8px; font-weight: 500; display: flex; justify-content: space-between; color: #94a3b8 !important;}
    
    .c-normal { color: #10b981 !important; }
    .c-alert { color: #f59e0b !important; }
    .c-critical { color: #ef4444 !important; }
    
    /* Botones de Streamlit personalizados */
    div.stButton > button {
        background: linear-gradient(180deg, #334155 0%, #1e293b 100%);
        color: #38bdf8 !important; border: 1px solid #0ea5e9; border-radius: 4px; font-weight: 600; transition: all 0.3s;
    }
    div.stButton > button:hover { background: #0ea5e9; color: #ffffff !important; box-shadow: 0 0 10px #0ea5e9; border: 1px solid #38bdf8; }
    
    /* Cajas Exportaciones */
    .export-box { background: #1e293b; padding: 20px; border-radius: 8px; border: 1px solid #38bdf8; margin-bottom: 10px; }
    .export-box h4 { color: #ffffff !important; margin-top: 0; }
    .export-box p { color: #cbd5e1 !important; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. GESTIÓN DE ESTADO (CAMPOS GENÉRICOS DE PROYECTO)
# ==========================================
if 'config' not in st.session_state:
    st.session_state.config = {
        'nombre_proyecto': 'SISTEMA DE GESTIÓN INTELIGENTE EMS',
        'ubicacion_proyecto': 'INSTALACIÓN ELÉCTRICA',
        'p_lim': 130.0, 'c_bat': 250.0, 'p_pv': 150.0,
        'v_nom': 220.0, 's_trafo': 1000.0, 'carga_noc': 40.0,
        'ps_activo': True, 'sim_run': 0
    }
cfg = st.session_state.config

# ==========================================
# 4. LÓGICA DE INGENIERÍA (CÁLCULOS)
# ==========================================
REAL_LOAD = [36, 36, 36, 36, 36, 40, 60, 90, 120, 145, 160, 175, 179.1, 140, 150, 155, 160, 165, 172, 175, 130, 90, 50, 36]
PV_BASE = [0, 0, 0, 0, 0, 0, 5, 25, 55, 90, 120, 140, 150, 140, 120, 90, 55, 25, 5, 0, 0, 0, 0, 0]

factor_pv = cfg['p_pv'] / 150.0 if cfg['p_pv'] > 0 else 0.0
pv_real = [round(v * factor_pv, 1) for v in PV_BASE]

soc_min = 0.20 * cfg['c_bat']
soc_max = cfg['c_bat']
energia = cfg['c_bat'] * 0.50

limite_operativo = cfg['p_lim'] if cfg['ps_activo'] else 9999.0

rows_ems = []
for i in range(24):
    p_teorica = REAL_LOAD[i] - pv_real[i]
    p_bat = 0.0
    
    if p_teorica > limite_operativo:
        req = p_teorica - limite_operativo
        p_bat = req if (energia - req) >= soc_min else max(0.0, energia - soc_min)
    elif 1 <= i <= 5: 
        p_bat = -cfg['carga_noc'] if (energia + cfg['carga_noc']) <= soc_max else -(soc_max - energia)
        
    p_red = p_teorica - p_bat
    energia -= p_bat
    soc = (energia / cfg['c_bat']) * 100.0
    
    rows_ems.append({
        'Hora': f"{i:02d}:00", 'P_Carga': REAL_LOAD[i], 'P_PV': pv_real[i],
        'P_Bat': round(p_bat, 1), 'P_Red': round(p_red, 1), 'SOC': round(soc, 1)
    })

df_ems = pd.DataFrame(rows_ems)

demanda_max = float(df_ems['P_Carga'].max())
demanda_recortada = float(df_ems['P_Red'].max())
reduccion_pico = demanda_max - demanda_recortada
inv_req = cfg['p_pv'] / 0.95 if cfg['p_pv'] > 0 else cfg['p_lim'] / 0.95
i_nom = (cfg['s_trafo'] * 1000.0) / (1.73205 * cfg['v_nom'])
icc_simetrica = i_nom / (5.75 / 100.0)
carg_sin = (demanda_max / cfg['s_trafo']) * 100.0
carg_con = (demanda_recortada / cfg['s_trafo']) * 100.0
soc_actual_estado = df_ems['SOC'].iloc[12]
estado_ps = "ACTIVO" if cfg['ps_activo'] else "INACTIVO"

# ==========================================
# 5. CABECERA DINÁMICA DEL PROYECTO
# ==========================================
st.markdown(f"""
<div class="scada-header">
    <div>
        <h2 class="scada-title">⚡ {cfg['nombre_proyecto']}</h2>
        <div class="scada-subtitle">UBICACIÓN: {cfg['ubicacion_proyecto']}</div>
    </div>
    <div style="text-align: right;">
        <div class="blinking">● ONLINE</div>
        <div style="color: #0ea5e9; font-size: 11px; margin-top: 4px; font-weight: 600;">PEAK SHAVING {estado_ps}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 6. BARRA LATERAL DE NAVEGACIÓN
# ==========================================
st.sidebar.markdown("<h3 style='color: #0ea5e9; margin-bottom: 20px;'>Navegación</h3>", unsafe_allow_html=True)
menu = st.sidebar.radio("Seleccione Módulo:", [
    "🏠 Dashboard Principal",
    "⚡ Análisis EMS",
    "📐 Diagrama Unifilar SCADA",
    "📄 Memoria Técnica",
    "📦 Exportaciones a CAD",
    "⚙️ Configuración del Proyecto"
], label_visibility="collapsed")

# ==========================================
# 7. VISTAS
# ==========================================

# ------------------------------------------
# VISTA 1: DASHBOARD
# ------------------------------------------
if menu == "🏠 Dashboard Principal":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="scada-card">
            <div class="scada-label">DEMANDA RED</div>
            <div class="scada-value">{demanda_recortada:.1f} <span class="scada-unit">kW</span></div>
            <div class="scada-sub"><span style="color:#94a3b8;">Original: {demanda_max:.1f} kW</span> <span class="c-normal">▼ {reduccion_pico:.1f} kW</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="scada-card">
            <div class="scada-label">ALMACENAMIENTO BESS</div>
            <div class="scada-value">{cfg['c_bat']:.0f} <span class="scada-unit">kWh</span></div>
            <div class="scada-sub"><span style="color:#94a3b8;">Química: LiFePO4</span> <span class="c-normal">SOC ~{soc_actual_estado:.0f}%</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="scada-card">
            <div class="scada-label">GENERACIÓN SOLAR</div>
            <div class="scada-value">{cfg['p_pv']:.0f} <span class="scada-unit">kWp</span></div>
            <div class="scada-sub"><span style="color:#94a3b8;">Inversor: {inv_req:.1f} kVA</span> <span class="c-normal">● NORMAL</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="scada-card">
            <div class="scada-label">TRAFO {cfg['s_trafo']:.0f} kVA</div>
            <div class="scada-value" style="color: {'#38bdf8' if carg_con < 85 else '#f59e0b'};">{carg_con:.1f} <span class="scada-unit">%</span></div>
            <div class="scada-sub"><span style="color:#94a3b8;">Cargabilidad Térmica</span> <span class="c-normal">● {'NORMAL' if carg_con < 85 else 'ALERTA'}</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<h4 style='color: #e2e8f0; margin-top:20px;'>Monitoreo de Potencia en Tiempo de Simulación</h4>", unsafe_allow_html=True)
    fig_main = go.Figure()
    fig_main.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Carga'], name='Demanda Bruta', line=dict(color='#3b82f6', width=2)))
    fig_main.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Red'], name='Consumo de Red', fill='tozeroy', line=dict(color='#10b981', width=3)))
    if cfg['ps_activo']:
        fig_main.add_trace(go.Scatter(x=df_ems['Hora'], y=[cfg['p_lim']]*24, name='Límite EMS', line=dict(color='#ef4444', width=2, dash='dash')))
    
    fig_main.update_layout(template="plotly_dark", height=400, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig_main, use_container_width=True)

    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    if col_b1.button("▶ EJECUTAR SIMULACIÓN", use_container_width=True):
        st.toast("✅ Simulación completada.")
    if col_b2.button("↻ RECALCULAR DATOS", use_container_width=True):
        st.rerun()
    if col_b3.button(f"⚡ {'DESACTIVAR' if cfg['ps_activo'] else 'ACTIVAR'} PEAK SHAVING", use_container_width=True):
        st.session_state.config['ps_activo'] = not cfg['ps_activo']
        st.rerun()

# ------------------------------------------
# VISTA 2: EMS / PEAK SHAVING
# ------------------------------------------
elif menu == "⚡ Análisis EMS":
    st.markdown("<h3 style='color: #0ea5e9;'>Análisis Detallado de Despacho BESS</h3>", unsafe_allow_html=True)
    fig_soc = go.Figure()
    fig_soc.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['SOC'], name='SOC BESS (%)', line=dict(color='#0ea5e9', width=3), fill='tozeroy', fillcolor='rgba(14, 165, 233, 0.2)'))
    fig_soc.add_trace(go.Scatter(x=df_ems['Hora'], y=[20]*24, name='Límite Reserva (20%)', line=dict(color='#ef4444', width=2, dash='dot')))
    fig_soc.update_layout(template="plotly_dark", height=300, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_soc, use_container_width=True)
    st.dataframe(df_ems.style.background_gradient(cmap='Blues', subset=['P_Red']), use_container_width=True)

# ------------------------------------------
# VISTA 3: UNIFILAR SCADA
# ------------------------------------------
elif menu == "📐 Diagrama Unifilar SCADA":
    st.markdown("<h3 style='color: #0ea5e9;'>Diagrama Unifilar Interactivo SCADA</h3>", unsafe_allow_html=True)
    
    fig_sld = go.Figure()
    fig_sld.update_xaxes(visible=False, range=[-100, 100]); fig_sld.update_yaxes(visible=False, range=[-70, 220])
    l_color = '#00f0ff'; t_color = '#f8fafc'
    
    fig_sld.add_trace(go.Scatter(x=[0, 0], y=[200, 150], mode='lines', line=dict(color=l_color, width=3), showlegend=False))
    fig_sld.add_annotation(x=30, y=190, text="ACOMETIDA RED PRINCIPAL", showarrow=False, font=dict(size=12, color=t_color))
    
    fig_sld.add_shape(type="circle", x0=-15, y0=115, x1=15, y1=145, line_color=l_color, line_width=3)
    fig_sld.add_shape(type="circle", x0=-15, y0=95, x1=15, y1=125, line_color=l_color, line_width=3)
    fig_sld.add_annotation(x=45, y=120, text=f"TRAFO {cfg['s_trafo']} kVA", showarrow=False, font=dict(size=12, color=t_color))
    
    fig_sld.add_trace(go.Scatter(x=[0, 0], y=[95, 60], mode='lines', line=dict(color=l_color, width=3), showlegend=False))
    fig_sld.add_shape(type="rect", x0=-12, y0=65, x1=12, y1=80, line_color=l_color, line_width=3, fillcolor='#0b1121')
    fig_sld.add_annotation(x=40, y=72, text="ITM PRINCIPAL", showarrow=False, font=dict(size=11, color=t_color))
    
    fig_sld.add_trace(go.Scatter(x=[0, 0], y=[60, 40], mode='lines', line=dict(color=l_color, width=3), showlegend=False))
    fig_sld.add_trace(go.Scatter(x=[-90, 90], y=[40, 40], mode='lines', line=dict(color=l_color, width=6), showlegend=False))
    fig_sld.add_annotation(x=0, y=47, text=f"BUS TGBT {cfg['v_nom']}V", showarrow=False, font=dict(size=13, color=t_color))
    
    fig_sld.add_trace(go.Scatter(x=[-50, -50], y=[40, 0], mode='lines', line=dict(color='#ef4444', width=3), showlegend=False))
    fig_sld.add_shape(type="rect", x0=-75, y0=-15, x1=-25, y1=0, line_color="#ef4444", line_width=3, fillcolor='rgba(239, 68, 68, 0.1)')
    fig_sld.add_annotation(x=-50, y=-7.5, text="CARGAS", showarrow=False, font=dict(size=12, color='#ef4444'))
    
    fig_sld.add_trace(go.Scatter(x=[50, 50], y=[40, 0], mode='lines', line=dict(color='#a855f7', width=3), showlegend=False))
    fig_sld.add_shape(type="rect", x0=20, y0=-15, x1=80, y1=0, line_color="#a855f7", line_width=3, fillcolor='rgba(168, 85, 247, 0.1)')
    fig_sld.add_annotation(x=50, y=-7.5, text="INVERSOR", showarrow=False, font=dict(size=12, color='#a855f7'))
    
    fig_sld.add_trace(go.Scatter(x=[35, 35], y=[-15, -40], mode='lines', line=dict(color='#f59e0b', width=3), showlegend=False))
    fig_sld.add_trace(go.Scatter(x=[65, 65], y=[-15, -40], mode='lines', line=dict(color='#10b981', width=3), showlegend=False))
    
    fig_sld.add_shape(type="rect", x0=20, y0=-60, x1=50, y1=-40, line_color="#f59e0b", line_width=3, fillcolor='rgba(245, 158, 11, 0.1)')
    fig_sld.add_annotation(x=35, y=-50, text="PV", showarrow=False, font=dict(size=12, color='#f59e0b'))
    fig_sld.add_shape(type="rect", x0=55, y0=-60, x1=85, y1=-40, line_color="#10b981", line_width=3, fillcolor='rgba(16, 185, 129, 0.1)')
    fig_sld.add_annotation(x=70, y=-50, text="BESS", showarrow=False, font=dict(size=12, color='#10b981'))

    fig_sld.update_layout(height=600, margin=dict(l=0, r=0, t=10, b=10), template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_sld, use_container_width=True)

# ------------------------------------------
# VISTA 4: MEMORIA TÉCNICA
# ------------------------------------------
elif menu == "📄 Memoria Técnica":
    st.markdown("<h3 style='color: #0ea5e9;'>Generación de Memoria Técnica Editable</h3>", unsafe_allow_html=True)
    st.markdown("El documento se generará utilizando el **Nombre del Proyecto** y la **Ubicación** definidos en la pestaña de configuración, con formato ejecutivo para informes de ingeniería.")
    
    def generar_docx():
        doc = Document()
        doc.add_heading('MEMORIA TÉCNICA DE INGENIERÍA', level=1)
        doc.add_paragraph(f"PROYECTO: {cfg['nombre_proyecto']}\nUBICACIÓN: {cfg['ubicacion_proyecto']}")
        
        doc.add_heading('1. OBJETIVOS', level=2)
        doc.add_paragraph(f"Implementación de un sistema EMS para gestión de la demanda eléctrica. Se limitará el consumo de la red a {cfg['p_lim']:.0f} kW utilizando un sistema de almacenamiento de {cfg['c_bat']:.0f} kWh acoplado con generación fotovoltaica de {cfg['p_pv']:.0f} kWp.")
        
        doc.add_heading('2. ESTUDIO TÉCNICO Y RESULTADOS', level=2)
        doc.add_paragraph(f"• Transformador Principal: {cfg['s_trafo']:.0f} kVA")
        doc.add_paragraph(f"• Tensión de Operación: {cfg['v_nom']:.0f} V")
        doc.add_paragraph(f"• Demanda Pico Original: {demanda_max:.1f} kW")
        doc.add_paragraph(f"• Demanda Pico Recortada: {demanda_recortada:.1f} kW")
        doc.add_paragraph(f"• Ahorro de Potencia (Peak Shaving): {reduccion_pico:.1f} kW")
        doc.add_paragraph(f"• Corriente Nominal (In): {i_nom:.1f} A")
        doc.add_paragraph(f"• Corriente Cortocircuito Simétrica (Icc): {icc_simetrica/1000.0:.2f} kA (requiere protección 50 kA AIC).")

        target = io.BytesIO()
        doc.save(target)
        return target.getvalue()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.download_button(
            label="📄 GENERAR Y DESCARGAR MEMORIA (.DOCX)",
            data=generar_docx(),
            file_name=f"Memoria_Tecnica_{cfg['nombre_proyecto'].replace(' ', '_')}.docx",
            mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            use_container_width=True
        )

# ------------------------------------------
# VISTA 5: EXPORTACIONES
# ------------------------------------------
elif menu == "📦 Exportaciones":
    st.markdown("<h3 style='color: #0ea5e9;'>Exportación a AutoCAD y Bases de Datos</h3>", unsafe_allow_html=True)
    
    def generate_dxf():
        lines = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC", "0", "SECTION", "2", "TABLES", "0", "ENDSEC", "0", "SECTION", "2", "BLOCKS", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
        def add_line(layer, x1, y1, x2, y2, color="7"):
            lines.extend(["0", "LINE", "8", layer, "62", color, "10", f"{x1:.2f}", "20", f"{y1:.2f}", "30", "0.0", "11", f"{x2:.2f}", "21", f"{y2:.2f}", "31", "0.0"])
        def add_circle(layer, cx, cy, r, color="7"):
            lines.extend(["0", "CIRCLE", "8", layer, "62", color, "10", f"{cx:.2f}", "20", f"{cy:.2f}", "30", "0.0", "40", f"{r:.2f}"])
        def add_text(layer, x, y, text, h=3.0, color="7"):
            lines.extend(["0", "TEXT", "8", layer, "62", color, "10", f"{x:.2f}", "20", f"{y:.2f}", "30", "0.0", "40", f"{h:.2f}", "1", str(text)])
        def add_box(layer, x1, y1, x2, y2, color="7"):
            add_line(layer, x1, y1, x2, y1, color); add_line(layer, x2, y1, x2, y2, color); add_line(layer, x2, y2, x1, y2, color); add_line(layer, x1, y2, x1, y1, color)

        # Cajetín y Titulos Dínámicos
        add_box("MARCO", -200, -150, 300, 250, "2")
        add_text("TEXTOS", -180, 230, f"PROYECTO: {cfg['nombre_proyecto'].upper()}", 5.0, "7")
        add_text("TEXTOS", -180, 220, f"UBICACION: {cfg['ubicacion_proyecto'].upper()}", 4.0, "7")
        
        # Red y Transformador
        add_line("MT", 50, 200, 50, 160, "4")
        add_text("TEXTOS", 55, 195, "RED PRINCIPAL DE MEDIA TENSION", 3.5, "7")
        add_circle("TRAFO", 50, 120, 15, "4"); add_circle("TRAFO", 50, 100, 15, "4")
        add_box("INFO", 80, 80, 200, 130, "3")
        add_text("TEXTOS", 85, 120, f"TRANSFORMADOR {cfg['s_trafo']:.0f} kVA", 3.5, "7")
        add_text("TEXTOS", 85, 110, f"Voltaje: {cfg['v_nom']:.0f} V", 3.5, "7")
        
        # Bus TGBT y Cargas
        add_line("BT", 50, 85, 50, 50, "4")
        add_line("BUS", -50, 50, 250, 50, "4")
        add_line("BT", -20, 50, -20, 10, "1"); add_box("EQUIPOS", -30, -10, -10, 10, "1")
        add_text("TEXTOS", -45, -20, "CARGAS DEL PROYECTO", 3.5, "7")
        
        # Inversor y BESS/PV
        add_line("BT", 150, 50, 150, 10, "6"); add_box("EQUIPOS", 110, -10, 190, 10, "6")
        add_text("TEXTOS", 115, 0, f"INVERSOR {inv_req:.1f} kVA", 3.5, "7")
        add_line("DC", 130, -10, 130, -40, "2"); add_box("EQUIPOS", 110, -60, 150, -40, "2")
        add_text("TEXTOS", 115, -50, f"PV {cfg['p_pv']:.0f} kWp", 3.0, "7")
        add_line("DC", 170, -10, 170, -40, "3"); add_box("EQUIPOS", 150, -60, 190, -40, "3")
        add_text("TEXTOS", 155, -50, f"BESS {cfg['c_bat']:.0f} kWh", 3.0, "7")

        lines.extend(["0", "ENDSEC", "0", "EOF"])
        return "\n".join(lines)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='export-box'><h4>Plano CAD de Ingeniería</h4><p>El diagrama incluye tu propio nombre de proyecto, cajetín técnico, transformador, TGBT y componentes de la microrred en capas diferenciadas de AutoCAD.</p></div>", unsafe_allow_html=True)
        st.download_button("📐 DESCARGAR PLANO CAD (.DXF)", generate_dxf().encode('utf-8'), f"Unifilar_{cfg['nombre_proyecto'].replace(' ','_')}.dxf", 'application/dxf', use_container_width=True)
    with c2:
        st.markdown("<div class='export-box'><h4>Datos Simulación</h4><p>Tabla de balance horario (24h) con demanda real, gestión EMS, y SOC de batería.</p></div>", unsafe_allow_html=True)
        st.download_button("📊 DESCARGAR RESULTADOS (.CSV)", df_ems.to_csv(index=False).encode('utf-8'), 'Resultados_EMS.csv', 'text/csv', use_container_width=True)

# ------------------------------------------
# VISTA 6: CONFIGURACIÓN
# ------------------------------------------
elif menu == "⚙️ Configuración del Proyecto":
    st.markdown("<h3 style='color: #0ea5e9;'>Panel General del Proyecto</h3>", unsafe_allow_html=True)
    
    st.markdown("<div class='scada-card'><h4>Nombres y Ubicación</h4>", unsafe_allow_html=True)
    st.session_state.config['nombre_proyecto'] = st.text_input("Nombre del Proyecto:", cfg['nombre_proyecto'])
    st.session_state.config['ubicacion_proyecto'] = st.text_input("Ubicación del Sitio:", cfg['ubicacion_proyecto'])
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='scada-card'><h4>Parámetros Eléctricos y BESS</h4>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.config['p_lim'] = st.slider("Límite de Red (kW)", 80.0, 200.0, cfg['p_lim'], 5.0)
        st.session_state.config['c_bat'] = st.slider("Capacidad BESS (kWh)", 50.0, 1000.0, cfg['c_bat'], 10.0)
        st.session_state.config['p_pv'] = st.slider("Potencia PV (kWp)", 0.0, 300.0, cfg['p_pv'], 10.0)
    with c2:
        st.session_state.config['s_trafo'] = st.slider("Capacidad Trafo (kVA)", 315.0, 2000.0, cfg['s_trafo'], 50.0)
        st.session_state.config['v_nom'] = st.slider("Tensión BT (V)", 110.0, 480.0, cfg['v_nom'], 10.0)
        st.session_state.config['carga_noc'] = st.slider("Carga Nocturna BESS (kW)", 10.0, 100.0, cfg['carga_noc'], 5.0)
    st.markdown("</div>", unsafe_allow_html=True)
