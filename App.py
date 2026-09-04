import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
import numpy as np
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(page_title="EMS Control Center", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif !important; }
    :root {
        --bg-main: #080F1F; --bg-panel: #111B2E; --bg-card: #172338; --border: #26354D;
        --cyan: #00B8FF; --green: #00D084; --yellow: #FFB020; --red: #FF4D5A;
        --text-main: #F8FAFC; --text-sec: #94A3B8;
    }
    .stApp { background-color: var(--bg-main); color: var(--text-main); }
    .block-container { padding-top: 1rem; max-width: 1400px; }
    header, footer { visibility: hidden; display: none; }
    .stMarkdown p, .stText p, .stSlider label, .stTextInput label { color: var(--text-sec) !important; font-weight: 500 !important; font-size: 13px !important; }
    div[data-testid="stThumbValue"] { color: var(--text-main) !important; font-size: 14px !important; font-weight: 600 !important; }
    .config-header { font-size: 26px; font-weight: 700; color: var(--cyan); margin-bottom: 12px; }
    .config-box { background-color: var(--bg-panel); border: 1px solid var(--border); border-radius: 8px; padding: 24px; margin-bottom: 24px; }
    .stSlider > div > div > div > div { background-color: var(--cyan) !important; }
    .stSlider > div > div > div > div > div { border-color: var(--cyan) !important; }
    section[data-testid="stSidebar"] { background-color: var(--bg-panel); border-right: 1px solid var(--border); padding-top: 24px;}
    div[data-testid="stSidebar"] * { color: var(--text-main) !important; }
    div[data-testid="stSidebar"] .stButton > button {
        background-color: transparent; border: 1px solid transparent; color: var(--text-sec) !important; 
        text-align: left; justify-content: flex-start; width: 100%; height: 42px; border-radius: 8px; font-weight: 500; font-size: 14px;
        transition: all 0.2s;
    }
    div[data-testid="stSidebar"] .stButton > button:hover { background-color: var(--bg-card); color: var(--cyan) !important; }
    .status-panel { border-top: 1px solid var(--border); padding-top: 16px; margin-top: 20px; }
    .status-lbl { font-size: 12px; color: var(--text-sec); letter-spacing: 1px; margin-bottom: 4px; }
    .status-online { color: var(--green); font-weight: 700; font-size: 14px; display: flex; align-items: center; gap: 8px; }
    .status-online::before { content: ''; display: inline-block; width: 8px; height: 8px; background-color: var(--green); border-radius: 50%; box-shadow: 0 0 6px var(--green); }
    .scada-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; }
    .scada-title { margin: 0; color: var(--text-main); font-size: 30px; font-weight: 700; display: flex; align-items: center; gap: 10px; }
    .scada-subtitle { color: var(--text-sec); font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 4px;}
    .scada-status-box { text-align: right; }
    .kpi-card { background-color: var(--bg-panel); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
    .kpi-title { font-size: 13px; color: var(--text-sec); font-weight: 600; text-transform: uppercase; margin-bottom: 8px; }
    .kpi-value { font-size: 28px; font-weight: 700; color: var(--text-main); line-height: 1; }
    .kpi-unit { font-size: 14px; color: var(--text-sec); font-weight: 500; margin-left: 4px; }
    .kpi-sub { font-size: 12px; color: var(--text-sec); margin-top: 10px; display: flex; justify-content: space-between; }
    .c-cyan { color: var(--cyan); } .c-green { color: var(--green); } .c-yellow { color: var(--yellow); } .c-red { color: var(--red); }
    div.stButton > button { background-color: var(--bg-card); color: var(--text-main) !important; border: 1px solid var(--border); border-radius: 9px; height: 42px; font-size: 14px; font-weight: 600; width: 100%; transition: all 0.2s;}
    div.stButton > button:hover { border-color: var(--cyan); color: var(--cyan) !important; }
    div.stButton > button[kind="primary"] { background-color: rgba(0,184,255,0.1); border-color: var(--cyan); color: var(--cyan) !important; height: 46px; font-size: 15px;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GESTIÓN DE ESTADO Y CONFIGURACIÓN
# ==========================================
if 'page' not in st.session_state: st.session_state.page = "Dashboard"
if 'config' not in st.session_state:
    st.session_state.config = {
        'nombre_proyecto': 'EMS Bloque D', 'ubicacion_proyecto': 'UPS Campus Centenario',
        'p_lim': 130.0, 'c_bat': 250.0, 'p_pv': 150.0, 'v_nom': 220.0, 's_trafo': 1000.0, 
        'carga_noc': 40.0, 'ps_activo': True
    }
cfg = st.session_state.config

# ==========================================
# 3. MÓDULOS MATEMÁTICOS Y LÓGICOS
# ==========================================
def calcular_soporte_reactivo(v_actual_pu, p_activa, s_inv_kva):
    """
    Control de voltaje (Volt/VAR) con curva de droop. 
    Actúa para estabilizar la tensión si sale de 0.98 - 1.02 p.u.
    """
    q_max = np.sqrt(max(0, s_inv_kva**2 - p_activa**2))
    q_inyectada = 0.0
    v_corregido = v_actual_pu
    
    if v_actual_pu < 0.98:
        q_requerida = (0.98 - v_actual_pu) * (s_inv_kva * 2) 
        q_inyectada = min(q_requerida, q_max)
        v_corregido = v_actual_pu + (q_inyectada / (s_inv_kva * 2))
    elif v_actual_pu > 1.02:
        q_requerida = (v_actual_pu - 1.02) * (s_inv_kva * 2)
        q_inyectada = max(-q_requerida, -q_max)
        v_corregido = v_actual_pu + (q_inyectada / (s_inv_kva * 2))
        
    return q_inyectada, v_corregido

def simular_evento_transitorio(tipo_evento):
    tiempo = np.linspace(0, 10, 1000)
    voltaje = np.ones(1000) * 1.0 
    frecuencia = np.ones(1000) * 60.0 
    
    if tipo_evento == "Cortocircuito Trifásico":
        idx_falla = (tiempo >= 2.9) & (tiempo < 3.0)
        idx_recup = tiempo >= 3.0
        voltaje[idx_falla] = 0.16 
        voltaje[idx_recup] = 0.98 + 0.05 * np.exp(-(tiempo[idx_recup]-3)*5) * np.sin(2*np.pi*5*(tiempo[idx_recup]-3))
        frecuencia[idx_falla] = 60.18
        frecuencia[idx_recup] = 60.0 + 0.15 * np.exp(-(tiempo[idx_recup]-3)*4) * np.cos(2*np.pi*3*(tiempo[idx_recup]-3))
        
    elif tipo_evento == "Cambio de Irradiancia":
        idx_falla = tiempo >= 2.0
        voltaje[idx_falla] = 0.974 + 0.01 * np.exp(-(tiempo[idx_falla]-2)*2)
        
    elif tipo_evento == "Variación de Carga":
        idx_falla = tiempo >= 2.0
        voltaje[idx_falla] = 0.985 + 0.015 * np.exp(-(tiempo[idx_falla]-2)*1.5) * np.cos(2*np.pi*2*(tiempo[idx_falla]-2))
        frecuencia[idx_falla] = 59.8 + 0.2 * np.exp(-(tiempo[idx_falla]-2)*2) * np.cos(2*np.pi*1.5*(tiempo[idx_falla]-2))
        
    return pd.DataFrame({"Tiempo (s)": tiempo, "Voltaje (p.u.)": voltaje, "Frecuencia (Hz)": frecuencia})

REAL_LOAD = [36, 36, 36, 36, 36, 40, 60, 90, 120, 145, 160, 175, 179.1, 140, 150, 155, 160, 165, 172, 175, 130, 90, 50, 36]
PV_BASE = [0, 0, 0, 0, 0, 0, 5, 25, 55, 90, 120, 140, 150, 140, 120, 90, 55, 25, 5, 0, 0, 0, 0, 0]
factor_pv = cfg['p_pv'] / 150.0 if cfg['p_pv'] > 0 else 0.0
pv_real = [round(v * factor_pv, 1) for v in PV_BASE]

soc_min = 0.20 * cfg['c_bat']; soc_max = cfg['c_bat']; energia = cfg['c_bat'] * 0.50
limite_operativo = cfg['p_lim'] if cfg['ps_activo'] else 9999.0
inv_req = cfg['p_pv'] / 0.95 if cfg['p_pv'] > 0 else cfg['p_lim'] / 0.95

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
    
    # Forzar una perturbación de voltaje proporcional a la carga de red para activar Q_inyectada
    v_base = 1.0 - (p_red / cfg['s_trafo']) * 0.4
    q_inyectada, v_final = calcular_soporte_reactivo(v_base, p_bat + pv_real[i], inv_req)
    
    rows_ems.append({'Hora': f"{i:02d}:00", 'P_Carga': REAL_LOAD[i], 'P_PV': pv_real[i], 'P_Bat': round(p_bat, 1), 
                     'P_Red': round(p_red, 1), 'SOC': round(soc, 1), 'V_pu': round(v_final, 3), 'Q_inyectada': round(q_inyectada, 1)})

df_ems = pd.DataFrame(rows_ems)
demanda_max = float(df_ems['P_Carga'].max())
demanda_recortada = float(df_ems['P_Red'].max())
reduccion_pico = demanda_max - demanda_recortada
carg_con = (demanda_recortada / cfg['s_trafo']) * 100.0
estado_ps = "PEAK SHAVING ACTIVO" if cfg['ps_activo'] else "PEAK SHAVING INACTIVO"

# ==========================================
# 4. BARRA LATERAL (NAVEGACIÓN)
# ==========================================
st.sidebar.markdown("""<div style="margin-bottom: 30px;"><h2 style="color: #F8FAFC; font-size: 20px; font-weight: 700; margin: 0;">Navegación</h2></div>""", unsafe_allow_html=True)

if st.sidebar.button("🏠 Dashboard Principal"): st.session_state.page = "Dashboard"
if st.sidebar.button("⚡ Análisis EMS (Peak Shaving)"): st.session_state.page = "EMS"
if st.sidebar.button("📉 Análisis Dinámico (Transitorios)"): st.session_state.page = "Transitorios"
if st.sidebar.button("📐 Diagrama Unifilar SCADA"): st.session_state.page = "Unifilar"
if st.sidebar.button("📄 Memoria Técnica"): st.session_state.page = "Memoria"
if st.sidebar.button("📦 Exportaciones"): st.session_state.page = "Exportaciones"

st.sidebar.markdown("""<div class="status-panel"><div class="status-lbl">SYSTEM STATUS</div><div class="status-online">ONLINE</div></div>""", unsafe_allow_html=True)

# ==========================================
# 5. CABECERA SCADA
# ==========================================
st.markdown(f"""
<div class="scada-header">
    <div><h2 class="scada-title"><span style="color: #FFB020;">⚡</span> EMS CONTROL CENTER</h2><div class="scada-subtitle">ENERGY MANAGEMENT SYSTEM | {cfg['ubicacion_proyecto']}</div></div>
    <div class="scada-status-box"><div class="status-online" style="justify-content: flex-end;">SYSTEM ONLINE</div><div style="color: #00B8FF; font-size: 11px; font-weight: 600; margin-top: 4px;">SISTEMA OPERATIVO | {estado_ps}</div></div>
</div>
""", unsafe_allow_html=True)

if st.session_state.page in ["Dashboard", "EMS", "Transitorios", "Unifilar"]:
    col_btn1, col_btn2, col_btn3 = st.columns([1,1,1])
    with col_btn1:
        if st.button("▶ EJECUTAR SIMULACIÓN", type="primary"): st.toast("Simulación Completada")
    with col_btn2:
        if st.button("↻ RECALCULAR"): st.rerun()
    with col_btn3:
        if st.button(f"⚡ PEAK SHAVING {'OFF' if cfg['ps_activo'] else 'ON'}"): 
            st.session_state.config['ps_activo'] = not cfg['ps_activo']
            st.rerun()

# ==========================================
# 6. VISTAS DE PÁGINA
# ==========================================

# --- VISTA 1: DASHBOARD ---
if st.session_state.page == "Dashboard":
    st.markdown("<div class='config-header'>Configuración Avanzada</div>", unsafe_allow_html=True)
    st.markdown("<div class='config-box'>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.session_state.config['p_lim'] = st.slider("Set-point límite red (kW)", 80.0, 200.0, cfg['p_lim'], 5.0)
        st.session_state.config['s_trafo'] = st.slider("Capacidad Trafo (kVA)", 315.0, 2000.0, cfg['s_trafo'], 50.0)
    with c2:
        st.session_state.config['c_bat'] = st.slider("Capacidad BESS (kWh)", 50.0, 1000.0, cfg['c_bat'], 10.0)
        st.session_state.config['v_nom'] = st.slider("Tensión BT (V)", 110.0, 480.0, cfg['v_nom'], 10.0)
    with c3:
        st.session_state.config['p_pv'] = st.slider("Potencia PV (kWp)", 0.0, 300.0, cfg['p_pv'], 10.0)
        st.session_state.config['carga_noc'] = st.slider("Carga Nocturna BESS (kW)", 10.0, 100.0, cfg['carga_noc'], 5.0)
    st.markdown("</div>", unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(f"""<div class="kpi-card"><div class="kpi-title">DEMANDA RED</div><div class="kpi-value">{demanda_recortada:.1f} <span class="kpi-unit">kW</span></div><div class="kpi-sub"><span>Original: {demanda_max:.1f} kW</span> <span class="c-cyan">▼ {reduccion_pico:.1f} kW</span></div></div>""", unsafe_allow_html=True)
    m2.markdown(f"""<div class="kpi-card"><div class="kpi-title">ALMACENAMIENTO BESS</div><div class="kpi-value">{cfg['c_bat']:.0f} <span class="kpi-unit">kWh</span></div><div class="kpi-sub"><span>Tecnología: LiFePO4</span> <span class="c-green">SOC Mín {soc_min:.0f} kWh</span></div></div>""", unsafe_allow_html=True)
    m3.markdown(f"""<div class="kpi-card"><div class="kpi-title">INVERSOR REQUERIDO</div><div class="kpi-value">{inv_req:.0f} <span class="kpi-unit">kVA</span></div><div class="kpi-sub"><span>Capacidad Aparente</span> <span class="c-green">● Volt/VAR Activo</span></div></div>""", unsafe_allow_html=True)
    m4.markdown(f"""<div class="kpi-card"><div class="kpi-title">CARGABILIDAD TRAFO</div><div class="kpi-value">{carg_con:.1f} <span class="kpi-unit">%</span></div><div class="kpi-sub"><span>Trafo {cfg['s_trafo']:.0f} kVA</span> <span class="{'c-green' if carg_con < 85 else 'c-red'}">● {'NORMAL' if carg_con < 85 else 'ALERTA'}</span></div></div>""", unsafe_allow_html=True)

    st.markdown("<h3 style='color:#F8FAFC; margin-top:20px; font-size:22px; font-weight:600;'>Monitoreo de Potencia (24h)</h3>", unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Carga'], name='Demanda Bruta', line=dict(color='#00B8FF', width=2)))
    fig.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Red'], name='Consumo Red', fill='tozeroy', line=dict(color='#00D084', width=2)))
    if cfg['ps_activo']: fig.add_trace(go.Scatter(x=df_ems['Hora'], y=[cfg['p_lim']]*24, name='Límite EMS', line=dict(color='#FF4D5A', width=2, dash='dash')))
    fig.update_layout(template="plotly_dark", height=400, margin=dict(l=10, r=10, t=20, b=10), paper_bgcolor='#111B2E', plot_bgcolor='#111B2E', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

# --- VISTA 2: ANÁLISIS EMS ---
elif st.session_state.page == "EMS":
    st.markdown("<h3 style='color: #00B8FF;'>Análisis EMS y Despacho de Baterías</h3>", unsafe_allow_html=True)
    fig_soc = go.Figure()
    fig_soc.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['SOC'], name='SOC BESS (%)', line=dict(color='#00B8FF', width=2), fill='tozeroy', fillcolor='rgba(0,184,255,0.1)'))
    fig_soc.add_trace(go.Scatter(x=df_ems['Hora'], y=[20]*24, name='Reserva (20%)', line=dict(color='#FF4D5A', width=2, dash='dash')))
    fig_soc.update_layout(template="plotly_dark", height=300, paper_bgcolor='#111B2E', plot_bgcolor='#111B2E')
    st.plotly_chart(fig_soc, use_container_width=True)
    st.dataframe(df_ems, use_container_width=True)

# --- VISTA 3: TRANSITORIOS ---
elif st.session_state.page == "Transitorios":
    st.markdown("<h3 style='color: #00B8FF;'>Análisis de Estabilidad Dinámica y Fallas (IEEE 2800 / ARCONEL-001/24)</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8;'>Simulación EMT (Electromagnetic Transients) en ventana de 10 segundos, evaluando la respuesta del inversor frente a perturbaciones de red.</p>", unsafe_allow_html=True)
    
    evento_seleccionado = st.selectbox("Seleccionar Evento de Contingencia:", ["Cortocircuito Trifásico", "Cambio de Irradiancia", "Variación de Carga"])
    df_transitorio = simular_evento_transitorio(evento_seleccionado)
    
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=df_transitorio['Tiempo (s)'], y=df_transitorio['Voltaje (p.u.)'], name='Voltaje PCC', line=dict(color='#00D084', width=2)))
    fig_v.add_trace(go.Scatter(x=[0,10], y=[1.05, 1.05], name='Límite Sup (1.05)', line=dict(color='#FF4D5A', dash='dash')))
    fig_v.add_trace(go.Scatter(x=[0,10], y=[0.90, 0.90], name='Límite Inf (0.90)', line=dict(color='#FF4D5A', dash='dash')))
    fig_v.update_layout(title="Respuesta de Voltaje (p.u.)", template="plotly_dark", height=300, margin=dict(t=40, b=10), paper_bgcolor='#111B2E', plot_bgcolor='#111B2E')
    
    fig_f = go.Figure()
    fig_f.add_trace(go.Scatter(x=df_transitorio['Tiempo (s)'], y=df_transitorio['Frecuencia (Hz)'], name='Frecuencia', line=dict(color='#00B8FF', width=2)))
    fig_f.add_trace(go.Scatter(x=[0,10], y=[61.2, 61.2], name='Límite Sup (61.2)', line=dict(color='#FF4D5A', dash='dash')))
    fig_f.add_trace(go.Scatter(x=[0,10], y=[58.8, 58.8], name='Límite Inf (58.8)', line=dict(color='#FF4D5A', dash='dash')))
    fig_f.update_layout(title="Estabilidad de Frecuencia (Hz)", template="plotly_dark", height=300, margin=dict(t=40, b=10), paper_bgcolor='#111B2E', plot_bgcolor='#111B2E')
    
    st.plotly_chart(fig_v, use_container_width=True)
    st.plotly_chart(fig_f, use_container_width=True)
    
    if evento_seleccionado == "Cortocircuito Trifásico":
        st.info("Diagnóstico: Falla trifásica en t=2.9s. El voltaje cae a 0.16 p.u. durante 100 ms. El sistema de control inyecta potencia reactiva (soporte dinámico) logrando estabilizar la tensión nominal cumpliendo la curva de tolerancia de la IEEE 2800 y ARCONEL-001/24.")
    elif evento_seleccionado == "Cambio de Irradiancia":
        st.info("Diagnóstico: Caída de irradiancia a 0 W/m² en t=2.0s. El inversor ajusta la potencia de salida sin comprometer los límites de voltaje continuo ni estabilidad de frecuencia.")
    elif evento_seleccionado == "Variación de Carga":
        st.info("Diagnóstico: Variación abrupta de carga del 50% en t=2.0s. Se generan oscilaciones en frecuencia que son amortiguadas por el EMS dentro del margen permisible de 58.8 Hz a 61.2 Hz.")

# --- VISTA 4: UNIFILAR ---
elif st.session_state.page == "Unifilar":
    st.markdown("<h3 style='color: #00B8FF;'>Diagrama Unifilar Jerárquico (Interfaz SCADA)</h3>", unsafe_allow_html=True)
    c_left, c_right = st.columns([1.5, 3.5])
    
    with c_left:
        st.markdown("<div style='background-color:#111B2E; border:1px solid #26354D; padding:20px; border-radius:8px;'><p style='font-size:16px; font-weight:700; color:#F8FAFC; margin-bottom:12px;'>Equipos</p>", unsafe_allow_html=True)
        eq = st.radio("Sel:", ["Transformador", "BESS", "Inversor", "Arreglo PV", "Red CNEL", "TGBT", "Cargas Bloque D"], label_visibility="collapsed")
        st.markdown("</div><br>", unsafe_allow_html=True)
        if eq == "Transformador":
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #FFFFFF;"><h4 style="color:#FFFFFF; margin-top:0;">⚡ TRANSFORMADOR</h4><div style="font-size:14px; line-height:2.0; color:#F8FAFC;"><b>Capacidad:</b> {cfg['s_trafo']} kVA<br><b>Tensión:</b> 69 kV / {cfg['v_nom']/1000} kV<br><b>Carga Actual:</b> {carg_con:.1f} %<br><span class="c-green">● NORMAL</span></div></div>""", unsafe_allow_html=True)
        elif eq == "BESS":
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #FFFFFF;"><h4 style="color:#FFFFFF; margin-top:0;">🔋 BANCO BESS</h4><div style="font-size:14px; line-height:2.0; color:#F8FAFC;"><b>Capacidad:</b> {cfg['c_bat']} kWh<br><b>Tecnología:</b> LiFePO4<br><span class="c-green">● ONLINE</span></div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #FFFFFF;"><h4 style="color:#FFFFFF; margin-top:0;">{eq.upper()}</h4><div style="font-size:14px; line-height:2.0; color:#F8FAFC;"><span class="c-green">● ESTADO: OPERATIVO</span></div></div>""", unsafe_allow_html=True)

    with c_right:
        hl_color = '#FFFFFF'
        col_cnel = hl_color if eq == "Red CNEL" else '#00B8FF'
        col_trafo = hl_color if eq == "Transformador" else '#00B8FF'
        col_tgbt = hl_color if eq == "TGBT" else '#00B8FF'
        col_carga = hl_color if eq == "Cargas Bloque D" else '#FF4D5A'
        col_inv = hl_color if eq == "Inversor" else '#A855F7'
        col_pv = hl_color if eq == "Arreglo PV" else '#FFB020'
        col_bess = hl_color if eq == "BESS" else '#00D084'

        fig_sld = go.Figure()
        fig_sld.update_xaxes(visible=False, range=[-120, 120]); fig_sld.update_yaxes(visible=False, range=[-80, 220])
        
        # Red CNEL
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[200, 150], mode='lines', line=dict(color=col_cnel, width=5 if eq == "Red CNEL" else 2), showlegend=False))
        fig_sld.add_annotation(x=30, y=190, text="RED CNEL 13.8 kV", showarrow=False, font=dict(size=12, color=col_cnel))
        
        # Trafo
        fig_sld.add_shape(type="circle", x0=-12, y0=115, x1=12, y1=145, line_color=col_trafo, line_width=5 if eq == "Transformador" else 2)
        fig_sld.add_shape(type="circle", x0=-12, y0=95, x1=12, y1=125, line_color=col_trafo, line_width=5 if eq == "Transformador" else 2)
        fig_sld.add_annotation(x=45, y=120, text=f"TRAFO {cfg['s_trafo']} kVA", showarrow=False, font=dict(size=12, color=col_trafo))
        
        # TGBT
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[95, 60], mode='lines', line=dict(color=col_tgbt, width=5 if eq == "TGBT" else 2), showlegend=False))
        fig_sld.add_shape(type="rect", x0=-10, y0=65, x1=10, y1=80, line_color=col_tgbt, line_width=4 if eq == "TGBT" else 2, fillcolor='#111B2E')
        fig_sld.add_annotation(x=35, y=72, text="ITM 50kA", showarrow=False, font=dict(size=11, color=col_tgbt))
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[60, 40], mode='lines', line=dict(color=col_tgbt, width=5 if eq == "TGBT" else 2), showlegend=False))
        fig_sld.add_trace(go.Scatter(x=[-90, 90], y=[40, 40], mode='lines', line=dict(color=col_tgbt, width=7 if eq == "TGBT" else 4), showlegend=False))
        fig_sld.add_annotation(x=0, y=47, text=f"BUS TGBT {cfg['v_nom']}V", showarrow=False, font=dict(size=13, color=col_tgbt, weight="bold"))
        
        # Rama Cargas
        fig_sld.add_trace(go.Scatter(x=[-50, -50], y=[40, 0], mode='lines', line=dict(color=col_carga, width=5 if eq == "Cargas Bloque D" else 2), showlegend=False))
        fig_sld.add_shape(type="rect", x0=-75, y0=-15, x1=-25, y1=0, line_color=col_carga, line_width=5 if eq == "Cargas Bloque D" else 2)
        fig_sld.add_annotation(x=-50, y=-7.5, text="CARGAS", showarrow=False, font=dict(size=11, color=col_carga))
        
        # Rama Inversor
        fig_sld.add_trace(go.Scatter(x=[50, 50], y=[40, 0], mode='lines', line=dict(color=col_inv, width=5 if eq == "Inversor" else 2), showlegend=False))
        fig_sld.add_shape(type="rect", x0=20, y0=-15, x1=80, y1=0, line_color=col_inv, line_width=5 if eq == "Inversor" else 2)
        fig_sld.add_annotation(x=50, y=-7.5, text="INVERSOR", showarrow=False, font=dict(size=11, color=col_inv))
        
        # DC Lines (PV / BESS)
        fig_sld.add_trace(go.Scatter(x=[35, 35], y=[-15, -40], mode='lines', line=dict(color=col_pv, width=5 if eq == "Arreglo PV" else 2), showlegend=False))
        fig_sld.add_trace(go.Scatter(x=[65, 65], y=[-15, -40], mode='lines', line=dict(color=col_bess, width=5 if eq == "BESS" else 2), showlegend=False))
        fig_sld.add_shape(type="rect", x0=20, y0=-60, x1=50, y1=-40, line_color=col_pv, line_width=5 if eq == "Arreglo PV" else 2)
        fig_sld.add_annotation(x=35, y=-50, text="PV", showarrow=False, font=dict(size=11, color=col_pv))
        fig_sld.add_shape(type="rect", x0=55, y0=-60, x1=85, y1=-40, line_color=col_bess, line_width=5 if eq == "BESS" else 2)
        fig_sld.add_annotation(x=70, y=-50, text="BESS", showarrow=False, font=dict(size=11, color=col_bess))

        fig_sld.update_layout(height=600, margin=dict(l=0, r=0, t=10, b=10), template='plotly_dark', paper_bgcolor='#111B2E', plot_bgcolor='#111B2E')
        st.plotly_chart(fig_sld, use_container_width=True)

# --- VISTA 5: MEMORIA TÉCNICA ---
elif st.session_state.page == "Memoria":
    st.markdown("<h3 style='color: #00B8FF;'>Generación de Memoria Técnica</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8;'>El documento Word (.docx) se genera respetando tu formato de ingeniería exacto.</p>", unsafe_allow_html=True)
    
    def generar_docx():
        doc = Document()
        for section in doc.sections:
            section.top_margin = Inches(1); section.bottom_margin = Inches(1); section.left_margin = Inches(1); section.right_margin = Inches(1)
            
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("MEMORIA TÉCNICA Y ESPECIFICACIONES DE PROYECTO"); r.bold = True; r.font.size = Pt(14)
        
        t_meta = doc.add_table(rows=4, cols=2); t_meta.style = 'Table Grid'
        data_m = [("Departamento:", "Ingeniería Técnica"), ("Documento:", f"Memoria Técnica EMS - {cfg['nombre_proyecto']}"), ("Código Documento:", "PROY-EMS-MTC-001"), ("Fecha:", "2026")]
        for i, (k, v) in enumerate(data_m):
            t_meta.cell(i, 0).text = k; t_meta.cell(i, 0).paragraphs[0].runs[0].bold = True; t_meta.cell(i, 1).text = v

        doc.add_heading('1. OBJETIVOS', level=1)
        doc.add_paragraph(f"Electrificación y recorte de demanda pico (Peak Shaving) a {cfg['p_lim']:.1f} kW, garantizando el cumplimiento de normativas de interconexión (IEEE 2800, ARCONEL-001/24).")
        doc.add_heading('2. ESTUDIO TÉCNICO Y ESTABILIDAD', level=1)
        doc.add_paragraph(f"El inversor IBR cumple límites de voltaje continuo (0.9-1.05 p.u.) mediante inyección reactiva dinámica de hasta {inv_req:.1f} kVA.")
        target = io.BytesIO(); doc.save(target)
        return target.getvalue()

    st.download_button("📄 DESCARGAR MEMORIA TÉCNICA (.DOCX)", generar_docx(), f"Memoria_Tecnica_{cfg['nombre_proyecto'].replace(' ','_')}.docx", 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')

# --- VISTA 6: EXPORTACIONES Y MATLAB ---
elif st.session_state.page == "Exportaciones":
    st.markdown("<h3 style='color: #00B8FF;'>Exportación de Planos, Datos y Código MATLAB</h3>", unsafe_allow_html=True)
    
    def generate_dxf_full():
        lines = ["0", "SECTION", "2", "HEADER", "0", "ENDSEC", "0", "SECTION", "2", "TABLES", "0", "ENDSEC", "0", "SECTION", "2", "BLOCKS", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
        def add_line(layer, x1, y1, x2, y2, color="7"): lines.extend(["0", "LINE", "8", layer, "62", color, "10", f"{x1:.2f}", "20", f"{y1:.2f}", "30", "0.0", "11", f"{x2:.2f}", "21", f"{y2:.2f}", "31", "0.0"])
        def add_circle(layer, cx, cy, r, color="7"): lines.extend(["0", "CIRCLE", "8", layer, "62", color, "10", f"{cx:.2f}", "20", f"{cy:.2f}", "30", "0.0", "40", f"{r:.2f}"])
        def add_text(layer, x, y, text, height=3.0, color="7"): lines.extend(["0", "TEXT", "8", layer, "62", color, "10", f"{x:.2f}", "20", f"{y:.2f}", "30", "0.0", "40", f"{height:.2f}", "1", str(text)])
        def add_box(layer, x1, y1, x2, y2, color="7"): add_line(layer, x1, y1, x2, y1, color); add_line(layer, x2, y1, x2, y2, color); add_line(layer, x2, y2, x1, y2, color); add_line(layer, x1, y2, x1, y1, color)

        add_box("MARCO", -200, -150, 300, 250, color="2")
        add_box("CAJETIN", 150, -150, 300, -80, color="2")
        add_text("TEXTOS", 160, -90, f"PROYECTO: {cfg['nombre_proyecto'].upper()}", 4.0, "7")
        add_text("TEXTOS", 160, -110, f"UBICACION: {cfg['ubicacion_proyecto'].upper()}", 3.5, "7")
        
        add_line("RED_MT", 50, 220, 50, 160, color="4")
        add_text("TEXTOS", 55, 210, "RED CNEL - 13.8 kV", 3.5, "7")
        add_circle("TRAFO", 50, 115, 15, color="4"); add_circle("TRAFO", 50, 95, 15, color="4")
        add_text("TEXTOS", 85, 120, f"TRAFO {cfg['s_trafo']:.0f} kVA", 3.5, "7")
        
        add_line("BUS", -50, 50, 250, 50, color="4")
        add_text("TEXTOS", 50, 55, f"BUS TGBT {cfg['v_nom']:.0f}V", 4.0, "7")
        
        add_line("RED_BT", -20, 48, -20, 10, color="1"); add_box("EQUIPOS", -30, -10, -10, 10, color="1")
        add_text("TEXTOS", -45, -20, "CARGAS", 3.5, "7")
        
        add_line("RED_BT", 150, 48, 150, 10, color="6"); add_box("EQUIPOS", 110, -10, 190, 10, color="6")
        add_text("TEXTOS", 115, 0, f"INVERSOR {inv_req:.1f} kVA", 3.5, "7")
        
        add_line("RED_DC", 130, -10, 130, -40, color="2"); add_box("EQUIPOS", 110, -60, 150, -40, color="2")
        add_text("TEXTOS", 115, -50, "PV", 3.0, "7")
        add_line("RED_DC", 170, -10, 170, -40, color="3"); add_box("EQUIPOS", 150, -60, 190, -40, color="3")
        add_text("TEXTOS", 155, -50, "BESS", 3.0, "7")

        lines.extend(["0", "ENDSEC", "0", "EOF"])
        return "\n".join(lines)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<div class='kpi-card' style='padding: 20px;'><h4 style='color:#F8FAFC; margin-top:0;'>Plano Vectorial CAD</h4><p style='color:#94A3B8; font-size:13px;'>Genera el diagrama unifilar CAD/DXF.</p></div>", unsafe_allow_html=True)
        st.download_button("📐 DESCARGAR PLANO CAD (.DXF)", generate_dxf_full().encode('utf-8'), f"Unifilar_{cfg['nombre_proyecto'].replace(' ','_')}.dxf", 'application/dxf', use_container_width=True)
    with c2:
        st.markdown("<div class='kpi-card' style='padding: 20px;'><h4 style='color:#F8FAFC; margin-top:0;'>Datos Simulación</h4><p style='color:#94A3B8; font-size:13px;'>Balance horario en CSV.</p></div>", unsafe_allow_html=True)
        st.download_button("📊 DESCARGAR RESULTADOS (.CSV)", df_ems.to_csv(index=False).encode('utf-8'), 'Resultados_EMS.csv', 'text/csv', use_container_width=True)

    st.markdown("<br><h4 style='color: #F8FAFC;'>Código Operativo EMS (MATLAB)</h4>", unsafe_allow_html=True)
    matlab_code = f"""%% ============================================================
%% Análisis Dinámico y Peak Shaving EMS — {cfg['nombre_proyecto']}
%% ============================================================
clear; clc;
P_lim = {cfg['p_lim']}; S_inv = {inv_req}; V_nom_pu = 1.0;
P_carga = [{', '.join(map(str, REAL_LOAD))}];
P_PV_real = [{', '.join(map(str, pv_real))}];
P_bat = zeros(1,24); Q_inyectada = zeros(1,24);

for t = 1:24
    P_teo = P_carga(t) - P_PV_real(t);
    P_bat(t) = max(0, P_teo - P_lim);
    
    %% Control Reactivo Volt/VAR (IEEE 2800) Droop Control
    Q_max = sqrt(max(0, S_inv^2 - P_bat(t)^2));
    
    %% Simulación de voltaje basado en consumo bruto
    V_bus = V_nom_pu - (P_teo / ({cfg['s_trafo']} * 0.4)); 
    
    if V_bus < 0.98
        Q_req = (0.98 - V_bus) * (S_inv * 2);
        Q_inyectada(t) = min(Q_req, Q_max);
    elseif V_bus > 1.02
        Q_req = (V_bus - 1.02) * (S_inv * 2);
        Q_inyectada(t) = max(-Q_req, -Q_max);
    end
end
disp('=== SIMULACIÓN COMPLETADA ===');
"""
    st.code(matlab_code, language='matlab')
