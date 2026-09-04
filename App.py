import streamlit as st
from core.ems_math import calcular_balance_24h
from ui import views

# ==========================================
# CONFIGURACIÓN BÁSICA Y ESTADOS
# ==========================================
st.set_page_config(page_title="EMS Control Center", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

if 'page' not in st.session_state: 
    st.session_state.page = "Dashboard"

if 'config' not in st.session_state:
    st.session_state.config = {
        'nombre_proyecto': 'EMS Bloque D', 'ubicacion_proyecto': 'UPS Campus Centenario',
        'p_lim': 130.0, 'c_bat': 250.0, 'p_pv': 150.0, 'v_nom': 220.0, 's_trafo': 1000.0, 
        'carga_noc': 40.0, 'ps_activo': True
    }

cfg = st.session_state.config

# ==========================================
# CÁLCULOS CENTRALIZADOS
# ==========================================
df_ems, kpis = calcular_balance_24h(cfg)

# ==========================================
# MENÚ LATERAL Y HEADER
# ==========================================
st.sidebar.markdown("""<div style="margin-bottom: 30px;"><h2 style="color: #F8FAFC; font-size: 20px; font-weight: 700; margin: 0;">Navegación</h2></div>""", unsafe_allow_html=True)

if st.sidebar.button("🏠 Dashboard Principal"): st.session_state.page = "Dashboard"
if st.sidebar.button("⚡ Análisis EMS (Peak Shaving)"): st.session_state.page = "EMS"
if st.sidebar.button("📉 Análisis Dinámico (Transitorios)"): st.session_state.page = "Transitorios"
if st.sidebar.button("📐 Diagrama Unifilar SCADA"): st.session_state.page = "Unifilar"
if st.sidebar.button("📄 Memoria Técnica"): st.session_state.page = "Memoria"
if st.sidebar.button("📦 Exportaciones"): st.session_state.page = "Exportaciones"

estado_ps = "PEAK SHAVING ACTIVO" if cfg['ps_activo'] else "PEAK SHAVING INACTIVO"

st.markdown(f"""
<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #26354D; padding-bottom: 16px; margin-bottom: 24px;">
    <div><h2 style="margin: 0; font-size: 30px; font-weight: 700;"><span style="color: #FFB020;">⚡</span> EMS CONTROL CENTER</h2><div style="color: #94A3B8; font-size: 12px; font-weight: 500; text-transform: uppercase;">ENERGY MANAGEMENT SYSTEM | {cfg['ubicacion_proyecto']}</div></div>
    <div style="text-align: right;"><div style="color: #00D084; font-weight: 700; font-size: 14px;">● SYSTEM ONLINE</div><div style="color: #00B8FF; font-size: 11px; font-weight: 600; margin-top: 4px;">SISTEMA OPERATIVO | {estado_ps}</div></div>
</div>
""", unsafe_allow_html=True)

if st.session_state.page in ["Dashboard", "EMS", "Transitorios", "Unifilar"]:
    c1, c2, c3 = st.columns(3)
    if c1.button("▶ EJECUTAR SIMULACIÓN", type="primary", use_container_width=True): st.toast("Simulación Completada")
    if c2.button("↻ RECALCULAR", use_container_width=True): st.rerun()
    if c3.button(f"⚡ PEAK SHAVING {'OFF' if cfg['ps_activo'] else 'ON'}", use_container_width=True): 
        st.session_state.config['ps_activo'] = not cfg['ps_activo']
        st.rerun()

# ==========================================
# RUTEO DE VISTAS (Llama a ui/views.py)
# ==========================================
if st.session_state.page == "Dashboard":
    views.render_dashboard(cfg, df_ems, kpis)
elif st.session_state.page == "EMS":
    views.render_ems(df_ems)
elif st.session_state.page == "Transitorios":
    views.render_transitorios()
elif st.session_state.page == "Unifilar":
    views.render_unifilar(cfg, kpis)
elif st.session_state.page == "Memoria":
    views.render_memoria(cfg, kpis)
elif st.session_state.page == "Exportaciones":
    views.render_exportaciones(cfg, df_ems, kpis)
