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
# 2. ESTILOS CSS AVANZADOS (SCADA DARK THEME)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * { font-family: 'Inter', sans-serif !important; }

    /* Paleta de colores SCADA */
    :root {
        --bg-main: #080F1F;
        --bg-panel: #111B2E;
        --bg-card: #172338;
        --border: #26354D;
        --cyan: #00B8FF;
        --green: #00D084;
        --yellow: #FFB020;
        --red: #FF4D5A;
        --text-main: #F8FAFC;
        --text-sec: #94A3B8;
    }

    /* Fondo principal y reseteo */
    .stApp { background-color: var(--bg-main); color: var(--text-main); }
    .block-container { padding-top: 1rem; max-width: 1400px; }
    header { visibility: hidden; }
    footer { visibility: hidden; }

    /* Barra lateral */
    section[data-testid="stSidebar"] { background-color: var(--bg-panel); border-right: 1px solid var(--border); }
    
    /* Navegación tipo píldora en el Sidebar */
    div[role="radiogroup"] > label {
        padding: 14px 16px !important;
        border-radius: 10px !important;
        margin-bottom: 8px !important;
        background-color: transparent;
        transition: all 0.2s ease;
        border: 1px solid transparent;
        cursor: pointer;
    }
    div[role="radiogroup"] > label:hover { background-color: var(--bg-card); }
    div[role="radiogroup"] > label[data-checked="true"] {
        background-color: var(--bg-card) !important;
        border-left: 4px solid var(--cyan) !important;
    }
    div[role="radiogroup"] > label p { font-size: 14px !important; font-weight: 500 !important; color: var(--text-sec) !important; }
    div[role="radiogroup"] > label[data-checked="true"] p { color: var(--cyan) !important; font-weight: 600 !important; }
    div[role="radiogroup"] > label span[data-baseweb="radio"] { display: none !important; } /* Ocultar círculo */

    /* SCADA Header */
    .scada-header {
        display: flex; justify-content: space-between; align-items: center; 
        background-color: var(--bg-panel);
        padding: 24px 32px; border: 1px solid var(--border); border-radius: 12px; margin-bottom: 24px;
    }
    .scada-title { margin: 0; color: var(--text-main); font-size: 28px; font-weight: 700; letter-spacing: 0.5px; }
    .scada-subtitle { color: var(--text-sec); font-size: 13px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px;}
    .scada-status { text-align: right; }
    .status-online { color: var(--green); font-weight: 700; font-size: 15px; text-shadow: 0 0 8px rgba(0, 208, 132, 0.4); display: flex; align-items: center; justify-content: flex-end; gap: 8px;}
    .status-online::before { content: ''; display: inline-block; width: 10px; height: 10px; background-color: var(--green); border-radius: 50%; box-shadow: 0 0 8px var(--green); }
    .ps-badge { color: var(--cyan); font-size: 12px; font-weight: 600; margin-top: 6px; }

    /* Tarjetas de Métricas */
    .scada-metric-card {
        background-color: var(--bg-card); border: 1px solid var(--border);
        border-radius: 12px; padding: 16px 20px; margin-bottom: 16px;
    }
    .scada-metric-label { font-size: 13px; color: var(--text-sec); font-weight: 600; text-transform: uppercase; margin-bottom: 12px; }
    .scada-metric-value { font-size: 32px; font-weight: 700; color: var(--text-main); line-height: 1; }
    .scada-metric-unit { font-size: 16px; color: var(--text-sec); font-weight: 500; margin-left: 4px; }
    .scada-metric-sub { font-size: 13px; margin-top: 12px; font-weight: 500; display: flex; justify-content: space-between; color: var(--text-sec); }

    /* Colores funcionales */
    .c-cyan { color: var(--cyan); }
    .c-green { color: var(--green); }
    .c-yellow { color: var(--yellow); }
    .c-red { color: var(--red); }

    /* Sliders como Tarjetas */
    div[data-testid="stSlider"] {
        background-color: var(--bg-card);
        padding: 16px 20px 24px 20px;
        border-radius: 12px;
        border: 1px solid var(--border);
    }
    div[data-testid="stSlider"] label { color: var(--cyan) !important; font-size: 13px !important; font-weight: 600 !important; text-transform: uppercase;}
    div[data-testid="stThumbValue"] { color: var(--text-main) !important; font-size: 20px !important; font-weight: 700 !important; }
    div[data-testid="stSliderTickBarMin"] { background-color: var(--cyan) !important; }

    /* Botones */
    div.stButton > button {
        background-color: var(--bg-panel); color: var(--text-main);
        border: 1px solid var(--border); border-radius: 9px; height: 42px; font-size: 14px; font-weight: 600;
        transition: all 0.2s ease; width: 100%;
    }
    div.stButton > button:hover { border-color: var(--cyan); color: var(--cyan); box-shadow: 0 0 8px rgba(0, 184, 255, 0.2); }
    div.stButton > button[kind="primary"] {
        background-color: rgba(0, 184, 255, 0.1); border-color: var(--cyan); color: var(--cyan); height: 46px; font-size: 15px; font-weight: 700;
    }
    div.stButton > button[kind="primary"]:hover { background-color: var(--cyan); color: var(--bg-main); box-shadow: 0 0 12px rgba(0, 184, 255, 0.4); }

    /* Texto general y bloques de código */
    .stMarkdown p, .stText p { color: var(--text-sec); font-size: 14px; }
    .stCodeBlock { background-color: var(--bg-card) !important; border: 1px solid var(--border) !important; border-radius: 10px !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. GESTIÓN DE ESTADO (CAMPOS GENÉRICOS)
# ==========================================
if 'config' not in st.session_state:
    st.session_state.config = {
        'p_lim': 130.0, 'c_bat': 250.0, 'p_pv': 150.0,
        'v_nom': 220.0, 's_trafo': 1000.0, 'carga_noc': 40.0,
        'ps_activo': True
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
    rows_ems.append({'Hora': f"{i:02d}:00", 'P_Carga': REAL_LOAD[i], 'P_PV': pv_real[i], 'P_Bat': round(p_bat, 1), 'P_Red': round(p_red, 1), 'SOC': round(soc, 1)})

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

# ==========================================
# 5. BARRA LATERAL SCADA
# ==========================================
st.sidebar.markdown("""
<div style="padding: 10px 0 24px 0;">
    <h2 style="color: #F8FAFC; font-size: 18px; margin: 0; font-weight: 700;">⚡ EMS CONTROL</h2>
    <div style="color: #00B8FF; font-size: 12px; font-weight: 500; letter-spacing: 1px;">Engineering Suite</div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<div style='font-size: 12px; color: #94A3B8; font-weight: 600; letter-spacing: 1px; margin-bottom: 8px;'>NAVEGACIÓN</div>", unsafe_allow_html=True)

menu = st.sidebar.radio("Navegación:", [
    "▣ Dashboard Principal",
    "⚡ Análisis EMS",
    "◈ Unifilar SCADA",
    "⚙ Configuración",
    "▤ Memoria Técnica",
    "□ Exportaciones & MATLAB"
], label_visibility="collapsed")

st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
st.sidebar.markdown("""
<div style="background-color: #172338; border: 1px solid #26354D; border-radius: 12px; padding: 16px;">
    <div style="font-size: 11px; color: #94A3B8; font-weight: 600; margin-bottom: 8px; letter-spacing: 1px;">SYSTEM STATUS</div>
    <div style="display: flex; align-items: center; gap: 8px; color: #00D084; font-weight: 700; font-size: 14px;">
        <div style="width: 8px; height: 8px; background-color: #00D084; border-radius: 50%; box-shadow: 0 0 8px #00D084;"></div> ONLINE
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 6. HEADER PRINCIPAL (BARRA DE ESTADO)
# ==========================================
estado_ps = "PEAK SHAVING ON" if cfg['ps_activo'] else "PEAK SHAVING OFF"
color_ps = "var(--cyan)" if cfg['ps_activo'] else "var(--text-sec)"

st.markdown(f"""
<div class="scada-header">
    <div>
        <h2 class="scada-title">⚡ EMS CONTROL CENTER</h2>
        <div class="scada-subtitle">Energy Management System | UPS Campus Centenario</div>
    </div>
    <div class="scada-status">
        <div class="status-online">SYSTEM ONLINE</div>
        <div class="ps-badge" style="color: {color_ps};">{estado_ps}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 7. BARRA DE ACCIONES (INTERACTIVA)
# ==========================================
col_act1, col_act2, col_act3, col_act4 = st.columns([2, 1.5, 1.5, 1.5])
with col_act1:
    if st.button("▶ EJECUTAR SIMULACIÓN", type="primary", use_container_width=True):
        st.toast("✅ Simulación completada.")
with col_act2:
    if st.button("↻ RECALCULAR", use_container_width=True):
        st.rerun()
with col_act3:
    if st.button("⚡ PEAK SHAVING", use_container_width=True):
        st.session_state.config['ps_activo'] = not cfg['ps_activo']
        st.rerun()
with col_act4:
    if st.button("📊 ANALIZAR", use_container_width=True):
        st.info("Icc: 45.6 kA | Flicker Plt: 1.12 | Estado Normal")

st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)

# ==========================================
# 8. VISTAS DEL SISTEMA
# ==========================================

# ------------------------------------------
# VISTA 1: DASHBOARD
# ------------------------------------------
if menu == "▣ Dashboard Principal":
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    with col_d1:
        st.markdown(f"""<div class="scada-metric-card">
            <div class="scada-metric-label">DEMANDA RED</div>
            <div class="scada-metric-value">{demanda_recortada:.1f} <span class="scada-metric-unit">kW</span></div>
            <div class="scada-metric-sub"><span>Original: {demanda_max:.1f} kW</span> <span class="c-cyan">▼ {reduccion_pico:.1f} kW</span></div>
        </div>""", unsafe_allow_html=True)
    with col_d2:
        st.markdown(f"""<div class="scada-metric-card">
            <div class="scada-metric-label">BESS DISPONIBLE</div>
            <div class="scada-metric-value">{cfg['c_bat']:.0f} <span class="scada-metric-unit">kWh</span></div>
            <div class="scada-metric-sub"><span>LiFePO4</span> <span class="c-green">SOC ~{soc_actual_estado:.0f}%</span></div>
        </div>""", unsafe_allow_html=True)
    with col_d3:
        st.markdown(f"""<div class="scada-metric-card">
            <div class="scada-metric-label">GENERACIÓN SOLAR</div>
            <div class="scada-metric-value">{cfg['p_pv']:.0f} <span class="scada-metric-unit">kWp</span></div>
            <div class="scada-metric-sub"><span>S_inv: {inv_req:.1f} kVA</span> <span class="c-green">● NORMAL</span></div>
        </div>""", unsafe_allow_html=True)
    with col_d4:
        c_color = "c-green" if carg_con < 85 else "c-red"
        st.markdown(f"""<div class="scada-metric-card">
            <div class="scada-metric-label">CARGA TRAFO ({cfg['s_trafo']:.0f} kVA)</div>
            <div class="scada-metric-value">{carg_con:.1f} <span class="scada-metric-unit">%</span></div>
            <div class="scada-metric-sub"><span>Antes: {carg_sin:.1f}%</span> <span class="{c_color}">● {'NORMAL' if carg_con < 85 else 'ALERTA'}</span></div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='font-size: 13px; color: #94A3B8; font-weight: 600; text-transform: uppercase; margin-bottom: 12px; margin-top: 16px;'>PERFIL ENERGÉTICO EN TIEMPO DE SIMULACIÓN</div>", unsafe_allow_html=True)
    
    fig_main = go.Figure()
    fig_main.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Carga'], name='Demanda Bruta', line=dict(color='#00B8FF', width=2)))
    fig_main.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Red'], name='Consumo Red', fill='tozeroy', line=dict(color='#00D084', width=3)))
    if cfg['ps_activo']:
        fig_main.add_trace(go.Scatter(x=df_ems['Hora'], y=[cfg['p_lim']]*24, name='Límite EMS', line=dict(color='#FF4D5A', width=2, dash='dash')))
    
    fig_main.update_layout(
        template="plotly_dark", height=420, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor='#111B2E', plot_bgcolor='#111B2E',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, gridcolor='#26354D'), yaxis=dict(showgrid=True, gridcolor='#26354D')
    )
    st.plotly_chart(fig_main, use_container_width=True)

# ------------------------------------------
# VISTA 2: CONFIGURACIÓN
# ------------------------------------------
elif menu == "⚙ Configuración":
    st.markdown("<div style='font-size: 14px; color: #F8FAFC; font-weight: 700; margin-bottom: 24px; letter-spacing: 1px;'>CONFIGURACIÓN DEL SISTEMA</div>", unsafe_allow_html=True)
    
    st.markdown("<div style='color: #00B8FF; font-size: 13px; font-weight: 700; margin-bottom: 12px;'>[ ⚡ RED ELÉCTRICA ]</div>", unsafe_allow_html=True)
    col_c1, col_c2 = st.columns(2)
    st.session_state.config['p_lim'] = col_c1.slider("Límite de red (kW)", 80.0, 200.0, cfg['p_lim'], 5.0)
    st.session_state.config['s_trafo'] = col_c2.slider("Capacidad Trafo (kVA)", 315.0, 2000.0, cfg['s_trafo'], 50.0)
    
    st.markdown("<div style='color: #00B8FF; font-size: 13px; font-weight: 700; margin-top: 24px; margin-bottom: 12px;'>[ 🔋 ALMACENAMIENTO ]</div>", unsafe_allow_html=True)
    col_c3, col_c4 = st.columns(2)
    st.session_state.config['c_bat'] = col_c3.slider("Capacidad BESS (kWh)", 50.0, 1000.0, cfg['c_bat'], 10.0)
    st.session_state.config['carga_noc'] = col_c4.slider("Carga nocturna (kW)", 10.0, 100.0, cfg['carga_noc'], 5.0)
    
    st.markdown("<div style='color: #00B8FF; font-size: 13px; font-weight: 700; margin-top: 24px; margin-bottom: 12px;'>[ ☀ GENERACIÓN ]</div>", unsafe_allow_html=True)
    col_c5, col_c6 = st.columns(2)
    st.session_state.config['p_pv'] = col_c5.slider("Potencia PV (kWp)", 0.0, 300.0, cfg['p_pv'], 10.0)
    st.session_state.config['v_nom'] = col_c6.slider("Tensión BT (V)", 110.0, 480.0, cfg['v_nom'], 10.0)

# ------------------------------------------
# VISTA 3: UNIFILAR SCADA
# ------------------------------------------
elif menu == "◈ Unifilar SCADA":
    c_left, c_right = st.columns([1.5, 3.5])
    
    with c_left:
        st.markdown("<div style='font-size: 13px; color: #94A3B8; font-weight: 600; margin-bottom: 12px;'>EQUIPOS EN LÍNEA</div>", unsafe_allow_html=True)
        eq_seleccionado = st.radio("Equipos", ["Transformador", "BESS", "Inversor", "Arreglo PV", "Red CNEL", "TGBT", "Cargas Bloque D"], label_visibility="collapsed")
        
        st.markdown("<div style='margin-top: 24px;'></div>", unsafe_allow_html=True)
        
        if eq_seleccionado == "Transformador":
            st.markdown(f"""<div class="scada-metric-card"><div class="scada-metric-label" style="color:var(--cyan) !important;">⚡ TRANSFORMADOR</div>
            <div style="font-size:15px; line-height:2.0; color:var(--text-main);"><b>Capacidad:</b> {cfg['s_trafo']} kVA<br><b>Tensión:</b> 69 kV / {cfg['v_nom']/1000} kV<br><b>Icc Simétrica:</b> {(icc_simetrica/1000):.2f} kA<br><b>Carga Actual:</b> {carg_con:.1f} %<br><br><span class="c-green" style="font-weight:700;">● ESTADO: NORMAL</span></div></div>""", unsafe_allow_html=True)
        elif eq_seleccionado == "BESS":
            st.markdown(f"""<div class="scada-metric-card"><div class="scada-metric-label" style="color:var(--cyan) !important;">🔋 BANCO BESS</div>
            <div style="font-size:15px; line-height:2.0; color:var(--text-main);"><b>Capacidad:</b> {cfg['c_bat']} kWh<br><b>Química:</b> LiFePO4<br><b>Energía Útil:</b> {cfg['c_bat']*0.8:.1f} kWh<br><b>SOC Reserva:</b> 20%<br><br><span class="c-green" style="font-weight:700;">● ESTADO: DISPONIBLE</span></div></div>""", unsafe_allow_html=True)
        elif eq_seleccionado == "Inversor":
            st.markdown(f"""<div class="scada-metric-card"><div class="scada-metric-label" style="color:var(--cyan) !important;">🔄 INVERSOR HÍBRIDO</div>
            <div style="font-size:15px; line-height:2.0; color:var(--text-main);"><b>Potencia:</b> {inv_req:.1f} kVA<br><b>Factor Potencia:</b> 0.95<br><b>Setpoint EMS:</b> {cfg['p_lim']} kW<br><b>Función:</b> Multimodo<br><br><span class="c-green" style="font-weight:700;">● ESTADO: ONLINE</span></div></div>""", unsafe_allow_html=True)
        elif eq_seleccionado == "Arreglo PV":
            st.markdown(f"""<div class="scada-metric-card"><div class="scada-metric-label" style="color:var(--cyan) !important;">☀️ ARREGLO SOLAR</div>
            <div style="font-size:15px; line-height:2.0; color:var(--text-main);"><b>Potencia Pico:</b> {cfg['p_pv']} kWp<br><b>Módulos:</b> PERC 550W<br><b>Área:</b> ~{int(cfg['p_pv']*1000/550)*2.2:.0f} m²<br><br><span class="c-green" style="font-weight:700;">● ESTADO: GENERANDO</span></div></div>""", unsafe_allow_html=True)
        elif eq_seleccionado == "Cargas Bloque D":
            st.markdown(f"""<div class="scada-metric-card"><div class="scada-metric-label" style="color:var(--cyan) !important;">🏭 CARGAS</div>
            <div style="font-size:15px; line-height:2.0; color:var(--text-main);"><b>Demanda Pico:</b> {demanda_max:.1f} kW<br><b>Demanda Base:</b> 36.0 kW<br><b>Flicker Plt:</b> 1.12<br><br><span class="c-yellow" style="font-weight:700;">● ESTADO: ALERTA P.Q.</span></div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="scada-metric-card"><div class="scada-metric-label" style="color:var(--cyan) !important;">{eq_seleccionado.upper()}</div>
            <div style="font-size:15px; line-height:2.0; color:var(--text-main);"><span class="c-green" style="font-weight:700;">● ESTADO: OPERATIVO</span></div></div>""", unsafe_allow_html=True)

    with c_right:
        fig_sld = go.Figure()
        fig_sld.update_xaxes(visible=False, range=[-100, 100]); fig_sld.update_yaxes(visible=False, range=[-70, 220])
        
        # Línea MT
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[200, 150], mode='lines', line=dict(color='#00B8FF', width=3), showlegend=False))
        fig_sld.add_annotation(x=30, y=190, text="RED CNEL 13.8 kV", showarrow=False, font=dict(size=13, color='#F8FAFC', family="Inter"))
        
        # Trafo
        fig_sld.add_shape(type="circle", x0=-15, y0=115, x1=15, y1=145, line_color='#00B8FF', line_width=3)
        fig_sld.add_shape(type="circle", x0=-15, y0=95, x1=15, y1=125, line_color='#00B8FF', line_width=3)
        fig_sld.add_annotation(x=45, y=120, text=f"TRAFO {cfg['s_trafo']} kVA", showarrow=False, font=dict(size=13, color='#F8FAFC', family="Inter"))
        
        # Línea a TGBT
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[95, 60], mode='lines', line=dict(color='#00B8FF', width=3), showlegend=False))
        fig_sld.add_shape(type="rect", x0=-12, y0=65, x1=12, y1=80, line_color='#00B8FF', line_width=3, fillcolor='#111B2E')
        fig_sld.add_annotation(x=40, y=72, text="ITM 50kA", showarrow=False, font=dict(size=12, color='#F8FAFC', family="Inter"))
        
        # Bus TGBT
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[60, 40], mode='lines', line=dict(color='#00B8FF', width=3), showlegend=False))
        fig_sld.add_trace(go.Scatter(x=[-90, 90], y=[40, 40], mode='lines', line=dict(color='#00B8FF', width=6), showlegend=False))
        fig_sld.add_annotation(x=0, y=47, text=f"BUS TGBT {cfg['v_nom']}V", showarrow=False, font=dict(size=14, color='#F8FAFC', family="Inter", weight="bold"))
        
        # Rama Cargas
        fig_sld.add_trace(go.Scatter(x=[-50, -50], y=[40, 0], mode='lines', line=dict(color='#FF4D5A', width=3), showlegend=False))
        fig_sld.add_shape(type="rect", x0=-75, y0=-15, x1=-25, y1=0, line_color="#FF4D5A", line_width=3, fillcolor='rgba(255, 77, 90, 0.1)')
        fig_sld.add_annotation(x=-50, y=-7.5, text="CARGAS", showarrow=False, font=dict(size=12, color='#FF4D5A', family="Inter", weight="bold"))
        
        # Rama Inversor
        fig_sld.add_trace(go.Scatter(x=[50, 50], y=[40, 0], mode='lines', line=dict(color='#00D084', width=3), showlegend=False))
        fig_sld.add_shape(type="rect", x0=20, y0=-15, x1=80, y1=0, line_color="#00D084", line_width=3, fillcolor='rgba(0, 208, 132, 0.1)')
        fig_sld.add_annotation(x=50, y=-7.5, text="INVERSOR", showarrow=False, font=dict(size=12, color='#00D084', family="Inter", weight="bold"))
        
        # DC Lines
        fig_sld.add_trace(go.Scatter(x=[35, 35], y=[-15, -40], mode='lines', line=dict(color='#FFB020', width=3), showlegend=False))
        fig_sld.add_trace(go.Scatter(x=[65, 65], y=[-15, -40], mode='lines', line=dict(color='#00D084', width=3), showlegend=False))
        
        # PV & BESS
        fig_sld.add_shape(type="rect", x0=20, y0=-60, x1=50, y1=-40, line_color="#FFB020", line_width=3, fillcolor='rgba(255, 176, 32, 0.1)')
        fig_sld.add_annotation(x=35, y=-50, text="PV", showarrow=False, font=dict(size=13, color='#FFB020', family="Inter", weight="bold"))
        fig_sld.add_shape(type="rect", x0=55, y0=-60, x1=85, y1=-40, line_color="#00D084", line_width=3, fillcolor='rgba(0, 208, 132, 0.1)')
        fig_sld.add_annotation(x=70, y=-50, text="BESS", showarrow=False, font=dict(size=13, color='#00D084', family="Inter", weight="bold"))

        fig_sld.update_layout(height=600, margin=dict(l=0, r=0, t=10, b=10), template='plotly_dark', paper_bgcolor='#111B2E', plot_bgcolor='#111B2E')
        st.plotly_chart(fig_sld, use_container_width=True)

# ------------------------------------------
# VISTA 4: EXPORTACIONES & MATLAB
# ------------------------------------------
elif menu == "□ Exportaciones & MATLAB":
    st.markdown("<h3 style='color: #0ea5e9;'>Exportación y Código MATLAB</h3>", unsafe_allow_html=True)
    
    matlab_code = f"""%% ============================================================
%% EMS Peak Shaving — UPS Bloque D
%% Generado automáticamente por Suite EMS Tesis
%% Normas: IEEE 2030.7-2017 / IEEE 1547-2018
%% ============================================================
clear; clc; close all;

%% Parámetros del sistema
P_lim    = {cfg['p_lim']};       % Límite red [kW]
C_bat    = {cfg['c_bat']};      % Capacidad BESS [kWh]
P_PV     = {cfg['p_pv']};       % Potencia PV instalada [kWp]
V_nom    = {cfg['v_nom']};        % Tensión nominal BT [V]
S_trafo  = {cfg['s_trafo']};    % Potencia trafo [kVA]
Z_trafo  = 5.75;          % Impedancia trafo [%]
FP_inv   = 0.95;          % Factor de potencia inversor

%% Datos medidos Bloque D
P_carga = [{', '.join(map(str, REAL_LOAD))}]; % [kW] 24h
P_PV_base = [{', '.join(map(str, PV_BASE))}];    % [kW] perfil FV base

%% Escalar perfil FV según potencia instalada
factor_PV = P_PV / 150;
P_PV_real = P_PV_base * factor_PV;

%% Algoritmo EMS determinístico (Peak Shaving + BESS)
SOC_min = 0.20 * C_bat;
SOC_max = C_bat;
E_bat   = zeros(1,24);
P_bat   = zeros(1,24);
P_red   = zeros(1,24);
SOC     = zeros(1,24);
E_act   = C_bat * 0.50; % Estado inicial 50%

for t = 1:24
    P_teo = P_carga(t) - P_PV_real(t);
    P_b   = 0;
    if P_teo > P_lim
        req = P_teo - P_lim;
        if (E_act - req) >= SOC_min
            P_b = req;
        else
            P_b = max(0, E_act - SOC_min);
        end
    elseif t >= 2 && t <= 6
        if (E_act + {cfg['carga_noc']}) <= SOC_max
            P_b = -{cfg['carga_noc']};
        else
            P_b = -(SOC_max - E_act);
        end
    end
    E_act     = E_act - P_b;
    P_bat(t)  = P_b;
    P_red(t)  = P_teo - P_b;
    E_bat(t)  = E_act;
    SOC(t)    = (E_act / C_bat) * 100;
end

%% Cálculos normativos
In_BT  = (S_trafo * 1000) / (sqrt(3) * V_nom);
Icc    = In_BT / (Z_trafo/100);
S_inv  = P_PV / FP_inv;
E_util = C_bat * 0.80;

fprintf('=== RESULTADOS EMS ===\\n');
fprintf('Demanda pico original : %.1f kW\\n', max(P_carga));
fprintf('Demanda pico recortada: %.1f kW\\n', max(P_red));
fprintf('Reducción de pico     : %.1f kW\\n', max(P_carga)-max(P_red));
fprintf('Icc transformador     : %.2f kA\\n', Icc/1000);
"""
    st.code(matlab_code, language='matlab')

# ------------------------------------------
# VISTA 5: MEMORIA TÉCNICA (Y RESTO DE MÓDULOS)
# ------------------------------------------
elif menu == "⚡ Análisis EMS":
    st.dataframe(df_ems.style.background_gradient(cmap='Blues', subset=['P_Red']), use_container_width=True)

elif menu == "▤ Memoria Técnica":
    st.markdown("<h3 style='color: #0ea5e9;'>Generación de Memoria Técnica</h3>", unsafe_allow_html=True)
    def generar_docx():
        doc = Document()
        doc.add_heading('MEMORIA TÉCNICA DE PROYECTO', level=1)
        doc.add_paragraph(f"Peak Shaving a {cfg['p_lim']} kW con BESS {cfg['c_bat']} kWh.")
        target = io.BytesIO()
        doc.save(target)
        return target.getvalue()
    
    st.download_button("📄 DESCARGAR MEMORIA (.DOCX)", generar_docx(), 'Memoria_EMS.docx', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', use_container_width=True)
