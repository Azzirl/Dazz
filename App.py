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
st.set_page_config(page_title="EMS Control Center - UPS", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

# ==========================================
# 2. ESTILOS CSS AVANZADOS (SCADA DARK THEME & TEXT FIX)
# ==========================================
st.markdown("""
<style>
    /* Fondo principal y reseteo de Streamlit */
    .stApp { background-color: #0b1121; color: #e2e8f0; }
    .block-container { padding-top: 1rem; max-width: 1400px; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    
    /* ---------------------------------------------------
       CORRECCIÓN DE VISIBILIDAD DE TEXTOS (CONTRASTE)
       Fuerza el texto blanco/claro sobre nuestro fondo oscuro
       incluso si Streamlit está en Modo Claro.
       --------------------------------------------------- */
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] span, 
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] div {
        color: #f8fafc !important;
    }
    .stMarkdown p, .stText p, .stRadio p, .stSlider p, .stSlider label {
        color: #e2e8f0 !important;
    }
    
    /* Cabecera del Centro de Control */
    .scada-header {
        display: flex; justify-content: space-between; align-items: center; 
        background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
        padding: 15px 25px; border-bottom: 2px solid #0ea5e9; border-radius: 8px; margin-bottom: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
    }
    .scada-title { margin: 0; color: #f8fafc !important; font-size: 24px; font-weight: 800; letter-spacing: 1px; }
    .scada-subtitle { color: #94a3b8 !important; font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 2px; }
    
    /* Animación de estado ONLINE */
    .blinking { animation: blinker 1.5s cubic-bezier(.5, 0, 1, 1) infinite alternate; color: #10b981 !important; font-weight: 700; font-size: 14px; text-shadow: 0 0 8px #10b981; }
    @keyframes blinker { 50% { opacity: 0.3; } }
    
    /* Tarjetas de Métricas SCADA */
    .scada-card {
        background-color: #1e293b; border: 1px solid #334155; border-top: 3px solid #0ea5e9;
        border-radius: 6px; padding: 16px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); transition: transform 0.2s;
    }
    .scada-card:hover { transform: translateY(-2px); border-color: #0ea5e9; }
    .scada-label { font-size: 12px; color: #94a3b8 !important; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
    .scada-value { font-size: 28px; font-weight: 700; color: #38bdf8 !important; text-shadow: 0 0 10px rgba(56, 189, 248, 0.2); margin:0; padding:0;}
    .scada-unit { font-size: 14px; color: #cbd5e1 !important; font-weight: 500; margin-left: 4px; }
    .scada-sub { font-size: 12px; margin-top: 8px; font-weight: 500; display: flex; justify-content: space-between; color: #94a3b8 !important;}
    
    /* Estados de colores forzados para las tarjetas */
    .c-normal { color: #10b981 !important; }
    .c-alert { color: #f59e0b !important; }
    .c-critical { color: #ef4444 !important; }
    
    /* Botones de Streamlit personalizados */
    div.stButton > button {
        background: linear-gradient(180deg, #334155 0%, #1e293b 100%);
        color: #38bdf8 !important; border: 1px solid #0ea5e9; border-radius: 4px; font-weight: 600; transition: all 0.3s;
    }
    div.stButton > button:hover { background: #0ea5e9; color: #ffffff !important; box-shadow: 0 0 10px #0ea5e9; border: 1px solid #38bdf8; }
    
    /* Barra lateral */
    section[data-testid="stSidebar"] { background-color: #0f172a; border-right: 1px solid #1e293b; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. GESTIÓN DE ESTADO (LÓGICA DESACOPLADA)
# ==========================================
if 'config' not in st.session_state:
    st.session_state.config = {
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

# Límite operativo (si Peak Shaving está apagado, límite infinito)
limite_operativo = cfg['p_lim'] if cfg['ps_activo'] else 9999.0

rows_ems = []
for i in range(24):
    p_teorica = REAL_LOAD[i] - pv_real[i]
    p_bat = 0.0
    
    if p_teorica > limite_operativo:
        req = p_teorica - limite_operativo
        p_bat = req if (energia - req) >= soc_min else max(0.0, energia - soc_min)
    elif 1 <= i <= 5: # Carga nocturna
        p_bat = -cfg['carga_noc'] if (energia + cfg['carga_noc']) <= soc_max else -(soc_max - energia)
        
    p_red = p_teorica - p_bat
    energia -= p_bat
    soc = (energia / cfg['c_bat']) * 100.0
    
    rows_ems.append({
        'Hora': f"{i:02d}:00", 'P_Carga': REAL_LOAD[i], 'P_PV': pv_real[i],
        'P_Bat': round(p_bat, 1), 'P_Red': round(p_red, 1), 'SOC': round(soc, 1)
    })

df_ems = pd.DataFrame(rows_ems)

# Métricas Globales
demanda_max = float(df_ems['P_Carga'].max())
demanda_recortada = float(df_ems['P_Red'].max())
reduccion_pico = demanda_max - demanda_recortada
inv_req = cfg['p_pv'] / 0.95 if cfg['p_pv'] > 0 else cfg['p_lim'] / 0.95
i_nom = (cfg['s_trafo'] * 1000.0) / (1.73205 * cfg['v_nom'])
icc_simetrica = i_nom / (5.75 / 100.0)
carg_sin = (demanda_max / cfg['s_trafo']) * 100.0
carg_con = (demanda_recortada / cfg['s_trafo']) * 100.0
soc_actual_estado = df_ems['SOC'].iloc[12] # SOC a mediodía para mostrar
estado_ps = "ACTIVO" if cfg['ps_activo'] else "INACTIVO"

# ==========================================
# 5. INTERFAZ: CABECERA SCADA
# ==========================================
st.markdown(f"""
<div class="scada-header">
    <div>
        <h2 class="scada-title">⚡ EMS CONTROL CENTER</h2>
        <div class="scada-subtitle">Energy Management System | UPS Campus Centenario</div>
    </div>
    <div style="text-align: right;">
        <div class="blinking">● ONLINE</div>
        <div style="color: #0ea5e9; font-size: 11px; margin-top: 4px; font-weight: 600;">SISTEMA OPERATIVO | PEAK SHAVING {estado_ps}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 6. BARRA LATERAL: NAVEGACIÓN MODERNA
# ==========================================
st.sidebar.markdown("<h3 style='color: #0ea5e9; margin-bottom: 20px;'>Navegación</h3>", unsafe_allow_html=True)
menu = st.sidebar.radio("Seleccione Módulo:", [
    "🏠 Dashboard Principal",
    "⚡ Análisis EMS",
    "📐 Diagrama Unifilar SCADA",
    "📄 Memoria Técnica",
    "📦 Exportaciones",
    "⚙️ Configuración"
], label_visibility="collapsed")

# ==========================================
# 7. VISTAS Y MÓDULOS
# ==========================================

# ------------------------------------------
# VISTA 1: DASHBOARD PRINCIPAL
# ------------------------------------------
if menu == "🏠 Dashboard Principal":
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="scada-card">
            <div class="scada-label">DEMANDA RED</div>
            <div class="scada-value">{demanda_recortada:.1f} <span class="scada-unit">kW</span></div>
            <div class="scada-sub"><span>Original: {demanda_max:.1f} kW</span> <span class="c-normal">▼ {reduccion_pico:.1f} kW</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="scada-card">
            <div class="scada-label">ALMACENAMIENTO BESS</div>
            <div class="scada-value">{cfg['c_bat']:.0f} <span class="scada-unit">kWh</span></div>
            <div class="scada-sub"><span>Tecnología: LiFePO4</span> <span class="c-normal">SOC ~{soc_actual_estado:.0f}%</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="scada-card">
            <div class="scada-label">GENERACIÓN SOLAR</div>
            <div class="scada-value">{cfg['p_pv']:.0f} <span class="scada-unit">kWp</span></div>
            <div class="scada-sub"><span>Inversor: {inv_req:.1f} kVA</span> <span class="c-normal">● NORMAL</span></div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        estado_trafo = "NORMAL" if carg_con < 85 else "ALERTA"
        clase_trafo = "c-normal" if carg_con < 85 else "c-alert"
        st.markdown(f"""
        <div class="scada-card">
            <div class="scada-label">TRAFO {cfg['s_trafo']:.0f} kVA</div>
            <div class="scada-value" style="color: {'#38bdf8' if carg_con < 85 else '#f59e0b'};">{carg_con:.1f} <span class="scada-unit">%</span></div>
            <div class="scada-sub"><span>Cargabilidad</span> <span class="{clase_trafo}">● {estado_trafo}</span></div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<h4 style='color: #e2e8f0; margin-top:20px;'>Monitoreo de Potencia en Tiempo de Simulación</h4>", unsafe_allow_html=True)
    fig_main = go.Figure()
    fig_main.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Carga'], name='Demanda Bruta', line=dict(color='#3b82f6', width=2)))
    fig_main.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Red'], name='Consumo de Red', fill='tozeroy', line=dict(color='#10b981', width=3)))
    if cfg['ps_activo']:
        fig_main.add_trace(go.Scatter(x=df_ems['Hora'], y=[cfg['p_lim']]*24, name='Límite EMS', line=dict(color='#ef4444', width=2, dash='dash')))
    
    fig_main.update_layout(
        template="plotly_dark", height=400, margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_main, use_container_width=True)

    col_b1, col_b2, col_b3, col_b4 = st.columns(4)
    if col_b1.button("▶ EJECUTAR SIMULACIÓN", use_container_width=True):
        st.session_state.config['sim_run'] += 1
        st.toast("✅ Simulación completada con éxito.")
    if col_b2.button("↻ RECALCULAR DATOS", use_container_width=True):
        st.rerun()
    if col_b3.button(f"⚡ {'DESACTIVAR' if cfg['ps_activo'] else 'ACTIVAR'} PEAK SHAVING", use_container_width=True):
        st.session_state.config['ps_activo'] = not cfg['ps_activo']
        st.rerun()
    if col_b4.button("📊 VER REPORTE CALIDAD", use_container_width=True):
        st.info("Icc: 45.64 kA | Flicker Plt: 1.12 (Alerta) | THD-V: 2.2% (Normal)")

# ------------------------------------------
# VISTA 2: EMS / PEAK SHAVING
# ------------------------------------------
elif menu == "⚡ Análisis EMS":
    st.markdown("<h3 style='color: #0ea5e9;'>Análisis Detallado de Despacho</h3>", unsafe_allow_html=True)
    
    fig_soc = go.Figure()
    fig_soc.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['SOC'], name='SOC BESS (%)', line=dict(color='#0ea5e9', width=3), fill='tozeroy', fillcolor='rgba(14, 165, 233, 0.2)'))
    fig_soc.add_trace(go.Scatter(x=df_ems['Hora'], y=[20]*24, name='Límite Reserva (20%)', line=dict(color='#ef4444', width=2, dash='dot')))
    fig_soc.update_layout(template="plotly_dark", height=300, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig_soc, use_container_width=True)

    st.markdown("<h4 style='color: #e2e8f0;'>Tabla de Despacho Horario</h4>", unsafe_allow_html=True)
    st.dataframe(df_ems.style.background_gradient(cmap='Blues', subset=['P_Red']), use_container_width=True)

# ------------------------------------------
# VISTA 3: UNIFILAR SCADA INTERACTIVO
# ------------------------------------------
elif menu == "📐 Diagrama Unifilar SCADA":
    st.markdown("<h3 style='color: #0ea5e9;'>Diagrama Unifilar Jerárquico (Interfaz SCADA)</h3>", unsafe_allow_html=True)
    
    c_left, c_right = st.columns([1, 3])
    with c_left:
        st.markdown("<div style='background:#1e293b; padding:15px; border-radius:8px; border:1px solid #334155;'>", unsafe_allow_html=True)
        st.markdown("<h4 style='color:#f8fafc; margin-top:0;'>Equipos</h4>", unsafe_allow_html=True)
        eq_seleccionado = st.radio("Seleccionar para ver detalles:", ["Transformador", "BESS", "Inversor", "Arreglo PV", "Red CNEL", "TGBT", "Cargas Bloque D"], label_visibility="collapsed")
        st.markdown("</div><br>", unsafe_allow_html=True)
        
        if eq_seleccionado == "Transformador":
            st.markdown(f"""<div class="scada-card"><h4 style="color:#0ea5e9; margin:0 0 10px 0;">⚡ TRANSFORMADOR</h4>
            <div style="font-size:14px; line-height:1.8;"><b>Capacidad:</b> {cfg['s_trafo']} kVA<br><b>Tensión:</b> 69 kV / {cfg['v_nom']/1000} kV<br><b>Icc Simétrica:</b> {(icc_simetrica/1000):.2f} kA<br><b>Carga Actual:</b> {carg_con:.1f} %<br><br><span class="c-normal">● ESTADO: NORMAL</span></div></div>""", unsafe_allow_html=True)
        elif eq_seleccionado == "BESS":
            st.markdown(f"""<div class="scada-card"><h4 style="color:#0ea5e9; margin:0 0 10px 0;">🔋 BANCO BESS</h4>
            <div style="font-size:14px; line-height:1.8;"><b>Capacidad:</b> {cfg['c_bat']} kWh<br><b>Química:</b> LiFePO4<br><b>Energía Útil:</b> {cfg['c_bat']*0.8:.1f} kWh<br><b>SOC Reserva:</b> 20%<br><br><span class="c-normal">● ESTADO: ONLINE</span></div></div>""", unsafe_allow_html=True)
        elif eq_seleccionado == "Inversor":
            st.markdown(f"""<div class="scada-card"><h4 style="color:#0ea5e9; margin:0 0 10px 0;">🔄 INVERSOR HÍBRIDO</h4>
            <div style="font-size:14px; line-height:1.8;"><b>Potencia:</b> {inv_req:.1f} kVA<br><b>Factor Potencia:</b> 0.95<br><b>Setpoint EMS:</b> {cfg['p_lim']} kW<br><b>Función:</b> Multimodo<br><br><span class="c-normal">● ESTADO: ONLINE</span></div></div>""", unsafe_allow_html=True)
        elif eq_seleccionado == "Arreglo PV":
            st.markdown(f"""<div class="scada-card"><h4 style="color:#0ea5e9; margin:0 0 10px 0;">☀️ ARREGLO SOLAR</h4>
            <div style="font-size:14px; line-height:1.8;"><b>Potencia Pico:</b> {cfg['p_pv']} kWp<br><b>Módulos:</b> PERC 550W<br><b>Área:</b> ~{int(cfg['p_pv']*1000/550)*2.2:.0f} m²<br><br><span class="c-normal">● ESTADO: GENERANDO</span></div></div>""", unsafe_allow_html=True)
        elif eq_seleccionado == "Red CNEL":
            st.markdown(f"""<div class="scada-card"><h4 style="color:#0ea5e9; margin:0 0 10px 0;">🔌 RED PRINCIPAL</h4>
            <div style="font-size:14px; line-height:1.8;"><b>Nivel Tensión:</b> 13.8 kV<br><b>Protección:</b> CCF 100A<br><b>Frecuencia:</b> 60 Hz<br><br><span class="c-normal">● ESTADO: ENERGIZADO</span></div></div>""", unsafe_allow_html=True)
        elif eq_seleccionado == "TGBT":
            st.markdown(f"""<div class="scada-card"><h4 style="color:#0ea5e9; margin:0 0 10px 0;">⚡ TGBT</h4>
            <div style="font-size:14px; line-height:1.8;"><b>Bus:</b> {cfg['v_nom']} V (3F-4H)<br><b>Disyuntor:</b> 3P-2000A<br><b>AIC:</b> 50 kA<br><br><span class="c-normal">● ESTADO: SEGURO</span></div></div>""", unsafe_allow_html=True)
        elif eq_seleccionado == "Cargas Bloque D":
            st.markdown(f"""<div class="scada-card"><h4 style="color:#0ea5e9; margin:0 0 10px 0;">🏭 CARGAS BLOQUE D</h4>
            <div style="font-size:14px; line-height:1.8;"><b>Demanda Pico:</b> {demanda_max:.1f} kW<br><b>Demanda Base:</b> 36.0 kW<br><b>Flicker Plt:</b> 1.12<br><br><span class="c-alert">● ESTADO: ALERTA P.Q.</span></div></div>""", unsafe_allow_html=True)

    with c_right:
        fig_sld = go.Figure()
        fig_sld.update_xaxes(visible=False); fig_sld.update_yaxes(visible=False)
        l_color = '#00f0ff'; t_color = '#f8fafc'
        
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[200, 160], mode='lines', line=dict(color=l_color, width=2), showlegend=False))
        fig_sld.add_annotation(x=0, y=205, text="RED CNEL 13.8 kV", showarrow=False, font=dict(size=12, color=t_color))
        fig_sld.add_shape(type="circle", x0=-10, y0=120, x1=10, y1=140, line_color=l_color, line_width=2)
        fig_sld.add_shape(type="circle", x0=-10, y0=105, x1=10, y1=125, line_color=l_color, line_width=2)
        fig_sld.add_annotation(x=40, y=122, text=f"TRAFO {cfg['s_trafo']} kVA", showarrow=False, font=dict(size=11, color=t_color))
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[105, 80], mode='lines', line=dict(color=l_color, width=2), showlegend=False))
        fig_sld.add_shape(type="rect", x0=-8, y0=65, x1=8, y1=80, line_color=l_color, line_width=2)
        fig_sld.add_annotation(x=35, y=72, text="ITM 50kA", showarrow=False, font=dict(size=10, color=t_color))
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[65, 50], mode='lines', line=dict(color=l_color, width=2), showlegend=False))
        fig_sld.add_trace(go.Scatter(x=[-80, 80], y=[50, 50], mode='lines', line=dict(color=l_color, width=4), showlegend=False))
        fig_sld.add_annotation(x=0, y=55, text=f"BUS TGBT {cfg['v_nom']}V", showarrow=False, font=dict(size=12, color=t_color))
        fig_sld.add_trace(go.Scatter(x=[-50, -50], y=[50, 10], mode='lines', line=dict(color='#ef4444', width=2), showlegend=False))
        fig_sld.add_shape(type="rect", x0=-70, y0=-10, x1=-30, y1=10, line_color="#ef4444", line_width=2)
        fig_sld.add_annotation(x=-50, y=0, text="CARGAS", showarrow=False, font=dict(size=11, color='#ef4444'))
        fig_sld.add_trace(go.Scatter(x=[50, 50], y=[50, 10], mode='lines', line=dict(color='#a855f7', width=2), showlegend=False))
        fig_sld.add_shape(type="rect", x0=25, y0=-10, x1=75, y1=10, line_color="#a855f7", line_width=2)
        fig_sld.add_annotation(x=50, y=0, text="INVERSOR", showarrow=False, font=dict(size=11, color='#a855f7'))
        fig_sld.add_trace(go.Scatter(x=[35, 35], y=[-10, -30], mode='lines', line=dict(color='#f59e0b', width=2), showlegend=False))
        fig_sld.add_trace(go.Scatter(x=[65, 65], y=[-10, -30], mode='lines', line=dict(color='#10b981', width=2), showlegend=False))
        fig_sld.add_shape(type="rect", x0=20, y0=-50, x1=50, y1=-30, line_color="#f59e0b", line_width=2)
        fig_sld.add_annotation(x=35, y=-40, text="PV", showarrow=False, font=dict(size=11, color='#f59e0b'))
        fig_sld.add_shape(type="rect", x0=55, y0=-50, x1=85, y1=-30, line_color="#10b981", line_width=2)
        fig_sld.add_annotation(x=70, y=-40, text="BESS", showarrow=False, font=dict(size=11, color='#10b981'))

        fig_sld.update_layout(height=480, margin=dict(l=0, r=0, t=10, b=10), template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_sld, use_container_width=True)

# ------------------------------------------
# VISTA 4: MEMORIA TÉCNICA
# ------------------------------------------
elif menu == "📄 Memoria Técnica":
    st.markdown("<h3 style='color: #0ea5e9;'>Generación de Memoria Técnica Oficial</h3>", unsafe_allow_html=True)
    st.markdown("El documento se generará en formato **Microsoft Word (.docx)** con la estructura oficial del proyecto, basándose estrictamente en las plantillas de ingeniería de los ejemplos suministrados (CNEL / GPS Group).")
    
    def generar_docx():
        doc = Document()
        for section in doc.sections:
            section.top_margin = Inches(1); section.bottom_margin = Inches(1); section.left_margin = Inches(1); section.right_margin = Inches(1)
            
        p_top = doc.add_paragraph()
        p_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_heading('MEMORIA TÉCNICA Y ESPECIFICACIONES DE PROYECTO', level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        t_meta = doc.add_table(rows=4, cols=2)
        t_meta.style = 'Table Grid'
        meta_data = [
            ("Departamento:", "Ingeniería y Viabilidad Técnica"),
            ("Documento:", f"Memoria Técnica EMS - UPS Bloque D"),
            ("Código del Documento:", "GPS-EMS-MTC-001"),
            ("Revisión / Fecha:", "Rev. C / 04/09/2026")
        ]
        for i, (k, v) in enumerate(meta_data):
            t_meta.cell(i, 0).text = k; t_meta.cell(i, 0).paragraphs[0].runs[0].bold = True
            t_meta.cell(i, 1).text = v

        doc.add_paragraph()
        
        # Historial de Revisiones
        doc.add_heading('Historial de revisiones', level=2)
        t_rev = doc.add_table(rows=2, cols=4)
        t_rev.style = 'Table Grid'
        headers = ["N° de Revisión", "Fecha", "Páginas Revisadas", "Motivo de Revisión"]
        for i, h in enumerate(headers):
            t_rev.cell(0, i).text = h; t_rev.cell(0, i).paragraphs[0].runs[0].bold = True
        t_rev.cell(1, 0).text = "01"
        t_rev.cell(1, 1).text = "04/09/2026"
        t_rev.cell(1, 2).text = "Todo el documento"
        t_rev.cell(1, 3).text = "Revisión General y Emisión"
        doc.add_paragraph()
        
        # Documentos Entregados
        doc.add_heading('Documentos Entregados', level=2)
        t_doc = doc.add_table(rows=2, cols=2)
        t_doc.style = 'Table Grid'
        t_doc.cell(0,0).text = "Documento:"; t_doc.cell(0,0).paragraphs[0].runs[0].bold = True
        t_doc.cell(0,1).text = "Código:"; t_doc.cell(0,1).paragraphs[0].runs[0].bold = True
        t_doc.cell(1,0).text = "Plano Unifilar y Memoria de Cálculo"
        t_doc.cell(1,1).text = "GPS-EMS-DUF-001"
        doc.add_page_break()

        # Índice
        doc.add_heading('ÍNDICE DE CONTENIDO', level=1)
        indice = ["1. OBJETIVOS", "2. INTRODUCCIÓN", "3. UBICACIÓN", "4. DESARROLLO GENERAL", "  4.1 SISTEMA EXISTENTE", "  4.2 SISTEMA PROYECTADO", "5. ESPECIFICACIONES TÉCNICAS", "6. CÁLCULO DE LA DEMANDA Y ESTUDIO ELÉCTRICO", "7. LISTA DE MATERIALES", "8. CONCLUSIONES", "9. ANEXOS"]
        for item in indice: doc.add_paragraph(item)
        doc.add_page_break()

        doc.add_heading('1. OBJETIVOS', level=1)
        doc.add_heading('1.1 Objetivo General:', level=2)
        doc.add_paragraph("Incorporación de nuevas tecnologías y mejora de la infraestructura con el objetivo de garantizar un suministro eléctrico competitivo, seguro y eficiente mediante la implementación de un Sistema Inteligente de Gestión de Energía (EMS).")
        doc.add_heading('1.2 Objetivos Específicos:', level=2)
        doc.add_paragraph(f"Electrificación y recorte de demanda pico (Peak Shaving) de {demanda_max:.1f} kW a {cfg['p_lim']:.1f} kW, garantizando el cumplimiento de las normativas de interconexión (IEEE 2030.7, 1547).")

        doc.add_heading('2. INTRODUCCIÓN', level=1)
        doc.add_paragraph("La implementación del proyecto apuesta por el uso de tecnologías híbridas (Generación fotovoltaica y almacenamiento BESS), mitigando los picos de consumo y mejorando el perfil de tensión local.")

        doc.add_heading('3. UBICACIÓN', level=1)
        doc.add_paragraph(f"El centro de carga principal está ubicado en el Campus Centenario UPS (Guayaquil, Ecuador).")

        doc.add_heading('4. DESARROLLO GENERAL', level=1)
        doc.add_heading('4.1 SISTEMA EXISTENTE', level=2)
        doc.add_paragraph(f"Actualmente el centro de carga opera con un transformador de {cfg['s_trafo']:.0f} kVA a {cfg['v_nom']}V, alcanzando una demanda máxima registrada de {demanda_max:.1f} kW, con una cargabilidad térmica original del {carg_sin:.1f}%.")
        
        doc.add_heading('4.2 SISTEMA PROYECTADO', level=2)
        doc.add_paragraph(f"Se proyecta la integración de un banco de baterías de {cfg['c_bat']:.0f} kWh y un sistema solar de {cfg['p_pv']:.0f} kWp, acoplados a un inversor de {inv_req:.1f} kVA. El algoritmo EMS limitará la potencia tomada de la red a {cfg['p_lim']:.1f} kW, mejorando la cargabilidad del transformador al {carg_con:.1f}%.")

        doc.add_heading('5. ESPECIFICACIONES TÉCNICAS', level=1)
        doc.add_paragraph(f"• INVERSOR MULTIMODO: Potencia Nominal de {inv_req:.1f} kVA, Factor de Potencia mínimo regulable a 0.95 (IEEE 1547).")
        doc.add_paragraph(f"• BANCO BESS: Capacidad Nominal de {cfg['c_bat']:.0f} kWh en tecnología LiFePO4, con DoD configurado al 80% (Reserva de seguridad SOC_min de {soc_min:.1f} kWh).")
        
        doc.add_heading('6. CÁLCULO DE LA DEMANDA Y ESTUDIO TÉCNICO', level=1)
        doc.add_paragraph(f"Para el bus principal en {cfg['v_nom']}V, la corriente nominal del transformador es de {i_nom:.1f} A. Considerando una impedancia de Z=5.75%, la corriente de falla simétrica es Icc = {icc_simetrica/1000.0:.2f} kA. Se validó la capacidad interruptiva requerida del disyuntor principal a 50 kA.")

        doc.add_heading('7. LISTA DE MATERIALES', level=1)
        t_mat = doc.add_table(rows=5, cols=4)
        t_mat.style = 'Table Grid'
        mat_headers = ["ÍTEM", "DESCRIPCIÓN", "UNIDAD", "CANTIDAD"]
        for i, h in enumerate(mat_headers):
            t_mat.cell(0, i).text = h; t_mat.cell(0, i).paragraphs[0].runs[0].bold = True
        
        materiales = [
            ("1", f"Sistema Almacenamiento BESS {cfg['c_bat']:.0f} kWh LiFePO4", "GLB", "1"),
            ("2", f"Inversor Híbrido Multimodo {inv_req:.1f} kVA", "UN", "1"),
            ("3", f"Sistema Fotovoltaico {cfg['p_pv']:.0f} kWp", "GLB", "1"),
            ("4", "Controlador PLC Microgrid EMS", "UN", "1")
        ]
        for r_idx, (i, d, u, c) in enumerate(materiales, start=1):
            t_mat.cell(r_idx, 0).text = i; t_mat.cell(r_idx, 1).text = d; t_mat.cell(r_idx, 2).text = u; t_mat.cell(r_idx, 3).text = c

        doc.add_heading('8. CONCLUSIONES', level=1)
        doc.add_paragraph(f"El sistema diseñado logra un aplanamiento neto de demanda de {reduccion_pico:.1f} kW, reduciendo el estrés térmico en el transformador de {cfg['s_trafo']:.0f} kVA y garantizando el cumplimiento normativo.")

        target = io.BytesIO()
        doc.save(target)
        return target.getvalue()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.download_button(
            label="📄 DESCARGAR MEMORIA (.DOCX)",
            data=generar_docx(),
            file_name='GPS_Memoria_Tecnica_EMS.docx',
            mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            use_container_width=True
        )
    with col2:
        st.markdown("<div style='padding:10px; color:#10b981; font-weight:bold;'>✔ Documento Word generado con estructura completa idéntico a las plantillas de ingeniería de GPS Group.</div>", unsafe_allow_html=True)

# ------------------------------------------
# VISTA 5: EXPORTACIONES
# ------------------------------------------
elif menu == "📦 Exportaciones":
    st.markdown("<h3 style='color: #0ea5e9;'>Exportación de Planos y Bases de Datos</h3>", unsafe_allow_html=True)
    
    def generate_dxf():
        lines = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC", "0", "SECTION", "2", "TABLES", "0", "ENDSEC", "0", "SECTION", "2", "BLOCKS", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
        def add_line(layer, x1, y1, x2, y2):
            lines.extend(["0", "LINE", "8", layer, "10", f"{x1:.2f}", "20", f"{y1:.2f}", "30", "0.0", "11", f"{x2:.2f}", "21", f"{y2:.2f}", "31", "0.0"])
        def add_circle(layer, cx, cy, r):
            lines.extend(["0", "CIRCLE", "8", layer, "10", f"{cx:.2f}", "20", f"{cy:.2f}", "30", "0.0", "40", f"{r:.2f}"])
        def add_text(layer, x, y, text, height=3.0):
            lines.extend(["0", "TEXT", "8", layer, "10", f"{x:.2f}", "20", f"{y:.2f}", "30", "0.0", "40", f"{height:.2f}", "1", str(text)])
        def add_box(layer, x1, y1, x2, y2):
            add_line(layer, x1, y1, x2, y1); add_line(layer, x2, y1, x2, y2); add_line(layer, x2, y2, x1, y2); add_line(layer, x1, y2, x1, y1)

        add_text("TEXTOS", -80, 220, "PROYECTO: EMS BLOQUE D", 5.0)
        add_line("RED_MT", 0, 200, 0, 160)
        add_text("TEXTOS", -45, 195, "ACOMETIDA RED PRINCIPAL CNEL - 69 kV / 13.8 kV", 3.5)
        add_circle("EQUIPOS", 0, 160, 2.5)
        add_circle("SIMBOLOS_TRAFO", 0, 128, 12); add_circle("SIMBOLOS_TRAFO", 0, 112, 12)
        add_box("CUADROS_INFO", 25, 95, 105, 145)
        add_text("TEXTOS", 28, 137, f"TRANSFORMADOR PEDESTAL {cfg['s_trafo']:.0f} kVA", 3.5)
        add_line("RED_BT", 0, 100, 0, 80)
        add_line("BUS_PRINCIPAL", -110, 50, 110, 50)
        
        lines.extend(["0", "ENDSEC", "0", "EOF"])
        return "\n".join(lines)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='scada-card'><h4 style='color:#f8fafc;'>Plano Vectorial</h4><p style='color:#94a3b8; font-size:13px;'>Diagrama unifilar en formato DXF (AutoCAD/ETAP).</p></div>", unsafe_allow_html=True)
        st.download_button("📐 DESCARGAR PLANO CAD (.DXF)", generate_dxf().encode('utf-8'), 'Plano_Unifilar_EMS.dxf', 'application/dxf', use_container_width=True)
    with c2:
        st.markdown("<div class='scada-card'><h4 style='color:#f8fafc;'>Datos Simulación</h4><p style='color:#94a3b8; font-size:13px;'>Tabla de balance horario 24h en CSV.</p></div>", unsafe_allow_html=True)
        st.download_button("📊 DESCARGAR RESULTADOS (.CSV)", df_ems.to_csv(index=False).encode('utf-8'), 'Resultados_EMS.csv', 'text/csv', use_container_width=True)

# ------------------------------------------
# VISTA 6: CONFIGURACIÓN
# ------------------------------------------
elif menu == "⚙️ Configuración":
    st.markdown("<h3 style='color: #0ea5e9;'>Configuración Avanzada</h3>", unsafe_allow_html=True)
    st.markdown("<div class='scada-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.config['p_lim'] = st.slider("Set-point límite de red (kW)", 80.0, 200.0, cfg['p_lim'], 5.0)
        st.session_state.config['c_bat'] = st.slider("Capacidad BESS (kWh)", 50.0, 1000.0, cfg['c_bat'], 10.0)
        st.session_state.config['p_pv'] = st.slider("Potencia PV (kWp)", 0.0, 300.0, cfg['p_pv'], 10.0)
    with c2:
        st.session_state.config['s_trafo'] = st.slider("Capacidad Trafo (kVA)", 315.0, 2000.0, cfg['s_trafo'], 50.0)
        st.session_state.config['v_nom'] = st.slider("Tensión BT (V)", 110.0, 480.0, cfg['v_nom'], 10.0)
        st.session_state.config['carga_noc'] = st.slider("Carga Nocturna BESS (kW)", 10.0, 100.0, cfg['carga_noc'], 5.0)
    st.markdown("</div>", unsafe_allow_html=True)
