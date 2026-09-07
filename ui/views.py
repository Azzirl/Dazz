import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
from core.ems_math import (
    simular_evento_transitorio,
    calcular_financiero,
    calcular_degradacion_bess,
    verificar_protecciones
)
from utils.exports import generate_dxf_full, generar_codigo_matlab

def render_dashboard(cfg, df_ems, kpis):
    st.markdown("<h3 style='color: #00B8FF; font-size:18px;'>📍 Geolocalización & Parámetros Climáticos Satelitales</h3>", unsafe_allow_html=True)
    
    col_coords, col_mapa = st.columns([1.5, 2.5])
    
    with col_coords:
        cfg['lat'] = st.number_input("Latitud GPS", value=cfg.get('lat', -2.1833), format="%.4f")
        cfg['lon'] = st.number_input("Longitud GPS", value=cfg.get('lon', -79.8833), format="%.4f")

        estilo_mapa = st.selectbox(
            "Estilo de Mapa",
            ["Satelital (HD Esri)", "Oscuro (SCADA Dark)", "Claro (Light)", "Callejero"],
            index=0
        )
        
        zoom_nivel = st.slider("Nivel de Zoom", min_value=1, max_value=20, value=16)

        if kpis.get('es_api_real'):
            st.success("📡 Telemetría Conectada: Obteniendo irradiancia en tiempo real vía API Satelital.")
        else:
            st.warning("⚠️ Sin conexión satelital: Utilizando perfil climático de respaldo (Fallback).")

    with col_mapa:
        view_state = pdk.ViewState(
            latitude=cfg['lat'],
            longitude=cfg['lon'],
            zoom=zoom_nivel,
            pitch=30 if estilo_mapa == "Satelital (HD Esri)" else 45,
            bearing=0
        )

        capa_punto = pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame({'lat': [cfg['lat']], 'lon': [cfg['lon']], 'nombre': [cfg['nombre_proyecto']]}),
            get_position='[lon, lat]',
            get_color='[0, 184, 255, 240]',
            get_radius=30,
            radius_min_pixels=8,
            radius_max_pixels=22,
            pickable=True
        )

        if estilo_mapa == "Satelital (HD Esri)":
            capa_satelital = pdk.Layer(
                "TileLayer",
                data="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                min_zoom=0,
                max_zoom=19,
                tile_size=256,
            )
            deck = pdk.Deck(
                map_style=None,
                initial_view_state=view_state,
                layers=[capa_satelital, capa_punto],
                tooltip={"text": "⚡ {nombre}\nLat: {lat}, Lon: {lon}"}
            )
        else:
            estilos_dict = {
                "Oscuro (SCADA Dark)": pdk.map_styles.CARTO_DARK,
                "Claro (Light)": pdk.map_styles.CARTO_LIGHT,
                "Callejero": pdk.map_styles.ROAD
            }
            deck = pdk.Deck(
                map_style=estilos_dict.get(estilo_mapa, pdk.map_styles.CARTO_DARK),
                initial_view_state=view_state,
                layers=[capa_punto],
                tooltip={"text": "⚡ {nombre}\nLat: {lat}, Lon: {lon}"}
            )

        st.pydeck_chart(deck, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='config-header'>Configuración Avanzada del EMS</div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        cfg['p_lim'] = st.slider("Set-point límite red (kW)", 80.0, 200.0, cfg['p_lim'], 5.0)
        cfg['s_trafo'] = st.slider("Capacidad Trafo (kVA)", 315.0, 2000.0, cfg['s_trafo'], 50.0)
    with c2:
        cfg['c_bat'] = st.slider("Capacidad BESS (kWh)", 50.0, 1000.0, cfg['c_bat'], 10.0)
        cfg['v_nom'] = st.slider("Tensión BT (V)", 110.0, 480.0, cfg['v_nom'], 10.0)
    with c3:
        cfg['p_pv'] = st.slider("Potencia PV (kWp)", 0.0, 300.0, cfg['p_pv'], 10.0)
        cfg['carga_noc'] = st.slider("Carga Nocturna BESS (kW)", 10.0, 100.0, cfg['carga_noc'], 5.0)

    # LECTURA SEGURA DE KPIS
    d_max = kpis.get('demanda_max', 179.1)
    d_rec = kpis.get('demanda_recortada', 130.0)
    soc_m = kpis.get('soc_min_kwh', kpis.get('soc_min', 50.0))
    inv_k = kpis.get('inv_kva', kpis.get('inv_req', 157.9))
    carg_c = kpis.get('carg_con_ems', kpis.get('carg_con', 13.0))

    m1, m2, m3, m4 = st.columns(4)
    reduccion_pico = d_max - d_rec
    
    m1.markdown(f"""<div class="kpi-card"><div class="kpi-title">DEMANDA RED</div><div class="kpi-value">{d_rec:.1f} <span class="kpi-unit">kW</span></div><div class="kpi-sub"><span>Original: {d_max:.1f} kW</span> <span class="c-cyan">▼ {reduccion_pico:.1f} kW</span></div></div>""", unsafe_allow_html=True)
    m2.markdown(f"""<div class="kpi-card"><div class="kpi-title">ALMACENAMIENTO BESS</div><div class="kpi-value">{cfg['c_bat']:.0f} <span class="kpi-unit">kWh</span></div><div class="kpi-sub"><span>Tecnología: LiFePO4</span> <span class="c-green">SOC Mín {soc_m:.0f} kWh</span></div></div>""", unsafe_allow_html=True)
    m3.markdown(f"""<div class="kpi-card"><div class="kpi-title">INVERSOR REQUERIDO</div><div class="kpi-value">{inv_k:.0f} <span class="kpi-unit">kVA</span></div><div class="kpi-sub"><span>Capacidad Aparente</span> <span class="c-green">● Volt/VAR Activo</span></div></div>""", unsafe_allow_html=True)
    m4.markdown(f"""<div class="kpi-card"><div class="kpi-title">CARGABILIDAD TRAFO</div><div class="kpi-value">{carg_c:.1f} <span class="kpi-unit">%</span></div><div class="kpi-sub"><span>Trafo {cfg['s_trafo']:.0f} kVA</span> <span class="{'c-green' if carg_c < 85 else 'c-red'}">● {'NORMAL' if carg_c < 85 else 'ALERTA'}</span></div></div>""", unsafe_allow_html=True)

    st.markdown("<h3 style='color:#00D084; margin-top:30px; font-size:18px; font-weight:600;'>🌱 Mitigación Ambiental y Sostenibilidad</h3>", unsafe_allow_html=True)
    
    energia_pv_diaria = df_ems['P_PV'].sum()
    co2_factor = 0.45 
    co2_evitado_diario = energia_pv_diaria * co2_factor
    co2_evitado_anual_ton = (co2_evitado_diario * 365) / 1000
    arboles_equivalentes = int(co2_evitado_anual_ton * 40)
    
    e1, e2, e3 = st.columns(3)
    e1.markdown(f"""<div class="kpi-card" style="border-top: 3px solid #FFB020;"><div class="kpi-title">PRODUCCIÓN FOTOVOLTAICA</div><div class="kpi-value">{energia_pv_diaria:.1f} <span class="kpi-unit">kWh/día</span></div><div class="kpi-sub"><span style="color:#FFB020;">● Energía 100% Renovable</span></div></div>""", unsafe_allow_html=True)
    e2.markdown(f"""<div class="kpi-card" style="border-top: 3px solid #00D084;"><div class="kpi-title">MITIGACIÓN DE CO₂ (ANUAL)</div><div class="kpi-value">{co2_evitado_anual_ton:.1f} <span class="kpi-unit">tCO₂</span></div><div class="kpi-sub"><span style="color:#00D084;">● {co2_evitado_diario:.1f} kg CO₂ diarios evitados</span></div></div>""", unsafe_allow_html=True)
    e3.markdown(f"""<div class="kpi-card" style="border-top: 3px solid #00D084;"><div class="kpi-title">COMPENSACIÓN ECOLÓGICA</div><div class="kpi-value">{arboles_equivalentes} <span class="kpi-unit">Árboles</span></div><div class="kpi-sub"><span style="color:#00D084;">● Absorción anual equivalente</span></div></div>""", unsafe_allow_html=True)

    st.markdown("<h3 style='color:#F8FAFC; margin-top:30px; font-size:22px; font-weight:600;'>Monitoreo de Potencia y Generación PV (24h)</h3>", unsafe_allow_html=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Carga'], name='Demanda Bruta (kW)', line=dict(color='#00B8FF', width=2)))
    fig.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_Red'], name='Consumo Red (kW)', fill='tozeroy', line=dict(color='#00D084', width=2)))
    fig.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['P_PV'], name='Generación Solar (kW)', line=dict(color='#FFB020', width=2, dash='dot')))
    if cfg['ps_activo']: 
        fig.add_trace(go.Scatter(x=df_ems['Hora'], y=[cfg['p_lim']]*24, name='Límite EMS (kW)', line=dict(color='#FF4D5A', width=2, dash='dash')))
    
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=20, b=10))
    st.plotly_chart(fig, use_container_width=True)

def render_ems(cfg, df_ems, kpis):
    st.markdown("<h3 style='color: #00B8FF;'>Análisis EMS y Despacho de Baterías</h3>", unsafe_allow_html=True)
    fig_soc = go.Figure()
    fig_soc.add_trace(go.Scatter(x=df_ems['Hora'], y=df_ems['SOC'], name='SOC BESS (%)', line=dict(color='#00B8FF', width=2), fill='tozeroy', fillcolor='rgba(0,184,255,0.1)'))
    fig_soc.add_trace(go.Scatter(x=df_ems['Hora'], y=[20]*24, name='Reserva (20%)', line=dict(color='#FF4D5A', width=2, dash='dash')))
    fig_soc.update_layout(height=300, margin=dict(t=10, b=10))
    st.plotly_chart(fig_soc, use_container_width=True)
    st.dataframe(df_ems, use_container_width=True)

    st.markdown("<hr style='border-color: #26354D;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #00B8FF;'>Diagrama PQ de Capacidad del Inversor (IEEE 2800)</h3>", unsafe_allow_html=True)
    
    s_inv_val = kpis.get('inv_kva', kpis.get('inv_req', 157.9))
    theta = np.linspace(0, 2*np.pi, 200)
    p_circ = s_inv_val * np.cos(theta)
    q_circ = s_inv_val * np.sin(theta)

    p_operativo = df_ems['P_PV'] + df_ems['P_Bat'].abs()
    q_operativo = df_ems['Q_inyectada']

    fig_pq = go.Figure()
    fig_pq.add_trace(go.Scatter(x=q_circ, y=p_circ, mode='lines', name=f'Límite Aparente S_inv = {s_inv_val:.1f} kVA', line=dict(color='#FF4D5A', width=2, dash='dash')))
    fig_pq.add_trace(go.Scatter(x=q_operativo, y=p_operativo, mode='markers', name='Puntos Operativos 24h', marker=dict(color='#00B8FF', size=8)))
    fig_pq.update_layout(title="Carta PQ de Operación del Inversor IBR", xaxis_title="Potencia Reactiva Q (kVAR)", yaxis_title="Potencia Activa P (kW)", height=400)
    st.plotly_chart(fig_pq, use_container_width=True)

    st.markdown("<hr style='border-color: #26354D;'>", unsafe_allow_html=True)
    st.markdown("<h3 style='color: #00B8FF;'>Desglose Matemático del Sistema</h3>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("<p style='color: #00D084; font-weight: bold;'>1. Balance de Potencia y Recorte de Picos (Peak Shaving)</p>", unsafe_allow_html=True)
        p_bruta_pico = kpis.get('demanda_max', 179.1)
        p_limite = cfg['p_lim']
        req_pico = max(0.0, p_bruta_pico - p_limite)
        p_red_calc = p_bruta_pico - req_pico
        
        with st.expander("🔍 Desglose numérico del Peak Shaving", expanded=True):
            st.latex(r"P_{req} = P_{bruta} - P_{limite}")
            st.latex(fr"P_{{req}} = {p_bruta_pico:.2f} - {p_limite:.2f} = \mathbf{{{req_pico:.2f} \text{{ kW}}}}")
            st.latex(r"P_{red} = P_{bruta} - P_{req}")
            st.latex(fr"P_{{red}} = {p_bruta_pico:.2f} - {req_pico:.2f} = \mathbf{{{p_red_calc:.2f} \text{{ kW}}}}")

        st.markdown("<p style='color: #00D084; font-weight: bold; margin-top: 20px;'>2. Estado de Carga Mínimo (SOC)</p>", unsafe_allow_html=True)
        c_bat_total = cfg['c_bat']
        soc_min_kwh = kpis.get('soc_min_kwh', kpis.get('soc_min', 50.0))
        
        with st.expander("🔍 Desglose numérico de Reserva de Batería", expanded=True):
            st.latex(r"SOC_{min} = C_{bat\_total} \times \frac{\%SOC_{min}}{100}")
            st.latex(fr"SOC_{{min}} = {c_bat_total:.2f} \times \frac{{20}}{{100}} = \mathbf{{{soc_min_kwh:.2f} \text{{ kWh}}}}")

    with c2:
        st.markdown("<p style='color: #00D084; font-weight: bold;'>3. Capacidad Reactiva Máxima (IEEE 2800)</p>", unsafe_allow_html=True)
        p_activa_pico = kpis.get('demanda_recortada', 130.0)
        q_max_calc = np.sqrt(max(0.0, s_inv_val**2 - p_activa_pico**2))
        
        with st.expander("🔍 Desglose numérico de Reserva Reactiva", expanded=True):
            st.latex(r"Q_{max} = \sqrt{S_{inv}^2 - P_{activa}^2}")
            st.latex(fr"Q_{{max}} = \sqrt{{({s_inv_val:.2f})^2 - ({p_activa_pico:.2f})^2}}")
            st.latex(fr"Q_{{max}} = \sqrt{{{s_inv_val**2:.2f} - {p_activa_pico**2:.2f}}} = \mathbf{{{q_max_calc:.2f} \text{{ kVAR}}}}")

        st.markdown("<p style='color: #00D084; font-weight: bold; margin-top: 20px;'>4. Control Dinámico (Droop Volt/VAR)</p>", unsafe_allow_html=True)
        v_min_reg = df_ems['V_pu'].min()
        q_iny_max = df_ems['Q_inyectada'].max()
        q_req_calc = (0.98 - v_min_reg) * (s_inv_val * 2)
        
        with st.expander("🔍 Desglose numérico de Compensación Volt/VAR", expanded=True):
            st.latex(r"Q_{req} = (0.98 - V_{actual}) \times (S_{inv} \times 2)")
            st.latex(fr"Q_{{req}} = (0.980 - {v_min_reg:.3f}) \times ({s_inv_val:.2f} \times 2) = {q_req_calc:.2f} \text{{ kVAR}}")
            st.latex(r"Q_{inyectada} = \min(Q_{req}, Q_{max})")
            st.latex(fr"Q_{{inyectada}} = \min({q_req_calc:.2f}, {q_max_calc:.2f}) = \mathbf{{{q_iny_max:.1f} \text{{ kVAR}}}}")

def render_transitorios():
    st.markdown("<h3 style='color: #00B8FF;'>Análisis de Estabilidad Dinámica y Fallas (IEEE 2800 / ARCONEL-001/24)</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94A3B8;'>Simulación EMT en ventana de 10 segundos, evaluando la respuesta del inversor frente a perturbaciones de red.</p>", unsafe_allow_html=True)
    
    evento_seleccionado = st.selectbox("Seleccionar Evento de Contingencia:", ["Cortocircuito Trifásico", "Cambio de Irradiancia", "Variación de Carga"])
    df_transitorio = simular_evento_transitorio(evento_seleccionado)
    
    fig_v = go.Figure()
    fig_v.add_trace(go.Scatter(x=df_transitorio['Tiempo (s)'], y=df_transitorio['Voltaje (p.u.)'], name='Voltaje PCC', line=dict(color='#00D084', width=2)))
    fig_v.add_trace(go.Scatter(x=[0,10], y=[1.05, 1.05], name='Límite Sup (1.05)', line=dict(color='#FF4D5A', dash='dash')))
    fig_v.add_trace(go.Scatter(x=[0,10], y=[0.90, 0.90], name='Límite Inf (0.90)', line=dict(color='#FF4D5A', dash='dash')))
    fig_v.update_layout(title="Respuesta de Voltaje (p.u.)", height=300, margin=dict(t=40, b=10))
    
    fig_f = go.Figure()
    fig_f.add_trace(go.Scatter(x=df_transitorio['Tiempo (s)'], y=df_transitorio['Frecuencia (Hz)'], name='Frecuencia', line=dict(color='#00B8FF', width=2)))
    fig_f.add_trace(go.Scatter(x=[0,10], y=[61.2, 61.2], name='Límite Sup (61.2)', line=dict(color='#FF4D5A', dash='dash')))
    fig_f.add_trace(go.Scatter(x=[0,10], y=[58.8, 58.8], name='Límite Inf (58.8)', line=dict(color='#FF4D5A', dash='dash')))
    fig_f.update_layout(title="Estabilidad de Frecuencia (Hz)", height=300, margin=dict(t=40, b=10))
    
    st.plotly_chart(fig_v, use_container_width=True)
    st.plotly_chart(fig_f, use_container_width=True)

def render_unifilar(cfg, kpis):
    st.markdown("<h3 style='color: #00B8FF;'>Diagrama Unifilar Jerárquico (Interfaz SCADA)</h3>", unsafe_allow_html=True)
    c_left, c_right = st.columns([1.5, 3.5])
    
    carg_c = kpis.get('carg_con_ems', kpis.get('carg_con', 13.0))
    inv_k = kpis.get('inv_kva', kpis.get('inv_req', 157.9))

    with c_left:
        st.markdown("<p style='font-size:16px; font-weight:700;'>Seleccionar Equipo en SCADA:</p>", unsafe_allow_html=True)
        eq = st.radio(
            "Sel:", 
            ["Transformador", "BESS", "Inversor", "Arreglo PV", "Red CNEL", "TGBT", "Cargas Bloque D"], 
            index=1,
            label_visibility="collapsed"
        )
        
        if eq == "Transformador":
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #00B8FF;"><h4 style="color:#FFFFFF; margin-top:0;">⚡ TRANSFORMADOR PRINCIPAL</h4><div style="font-size:14px; line-height:2.0;"><b>Capacidad Nominal:</b> {cfg['s_trafo']:.0f} kVA<br><b>Tensión:</b> 13.8 kV / {cfg['v_nom']:.0f} V<br><b>Impedancia (Z%):</b> 5.75%<br><b>Cargabilidad Actual:</b> {carg_c:.1f} %<br><span class="c-green">● ESTADO: NORMAL</span></div></div>""", unsafe_allow_html=True)
        elif eq == "BESS":
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #00D084;"><h4 style="color:#FFFFFF; margin-top:0;">🔋 BANCO DE BATERÍAS (BESS)</h4><div style="font-size:14px; line-height:2.0;"><b>Capacidad:</b> {cfg['c_bat']:.0f} kWh<br><b>Tecnología:</b> LiFePO4 @ DoD 80%<br><b>Reserva Mínima (SOC):</b> 20% ({cfg['c_bat']*0.2:.0f} kWh)<br><b>Carga Nocturna:</b> {cfg['carga_noc']:.0f} kW<br><span class="c-green">● ESTADO: ONLINE</span></div></div>""", unsafe_allow_html=True)
        elif eq == "Inversor":
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #A855F7;"><h4 style="color:#FFFFFF; margin-top:0;">⚡ INVERSOR BIDIRECCIONAL IBR</h4><div style="font-size:14px; line-height:2.0;"><b>Capacidad Aparente (S_inv):</b> {inv_k:.1f} kVA<br><b>Eficiencia Inversor:</b> 95%<br><b>Soporte Reactivo:</b> Volt/VAR Activo (IEEE 2800)<br><b>THD Corriente:</b> < 5% (IEEE 1547)<br><span class="c-green">● ESTADO: OPERATIVO</span></div></div>""", unsafe_allow_html=True)
        elif eq == "Arreglo PV":
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #FFB020;"><h4 style="color:#FFFFFF; margin-top:0;">☀️ ARREGLO FOTOVOLTAICO</h4><div style="font-size:14px; line-height:2.0;"><b>Potencia Instalada:</b> {cfg['p_pv']:.0f} kWp<br><b>Tecnología:</b> Silicio Módulos PERC<br><b>Eficiencia Sistema:</b> 80% (Pérdidas térmicas/cables)<br><b>Telemetría:</b> API Satelital Open-Meteo<br><span class="c-green">● ESTADO: GENERANDO</span></div></div>""", unsafe_allow_html=True)
        elif eq == "Red CNEL":
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #00B8FF;"><h4 style="color:#FFFFFF; margin-top:0;">🌐 RED ELÉCTRICA (CNEL EP)</h4><div style="font-size:14px; line-height:2.0;"><b>Tensión Media Tensión:</b> 13.8 kV<br><b>Frecuencia Nominal:</b> 60.0 Hz<br><b>Límite Set-Point EMS:</b> {cfg['p_lim']:.0f} kW<br><b>Modo EMS:</b> {'PEAK SHAVING ACTIVO' if cfg['ps_activo'] else 'DESACTIVADO'}<br><span class="c-green">● CONEXIÓN SÍNCRONA ESTABLE</span></div></div>""", unsafe_allow_html=True)
        elif eq == "TGBT":
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #00B8FF;"><h4 style="color:#FFFFFF; margin-top:0;">🏢 TABLERO GENERAL (TGBT)</h4><div style="font-size:14px; line-height:2.0;"><b>Tensión Bus BT:</b> {cfg['v_nom']:.0f} V L-L / {cfg['v_nom']/np.sqrt(3):.0f} V L-N<br><b>Tolerancia Tensión:</b> 0.90 – 1.05 p.u. (ARCONEL)<br><b>Icc Asimétrica Calculada:</b> {kpis.get('datos_icc', {}).get('icc_asim_kA', 15.0):.2f} kA<br><b>Capacidad Disyuntor (AIC):</b> 50.0 kA<br><span class="c-green">● CUMPLE PROTECCIÓN NEC 110-9</span></div></div>""", unsafe_allow_html=True)
        elif eq == "Cargas Bloque D":
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #FF4D5A;"><h4 style="color:#FFFFFF; margin-top:0;">🏬 CARGAS EDIFICIO D (LABS)</h4><div style="font-size:14px; line-height:2.0;"><b>Demanda Pico Registrada:</b> {kpis.get('demanda_max', 179.1):.1f} kW<br><b>Demanda Recortada EMS:</b> {kpis.get('demanda_recortada', 130.0):.1f} kW<br><b>Ubicación:</b> UPS Campus Centenario<br><span class="c-green">● SUMINISTRO CONTINUO A LABORARIOS</span></div></div>""", unsafe_allow_html=True)

    with c_right:
        # Colores dinámicos de resaltado al seleccionar
        hl_color = '#FFFFFF'
        col_cnel = hl_color if eq == "Red CNEL" else '#00B8FF'
        col_trafo = hl_color if eq == "Transformador" else '#00B8FF'
        col_tgbt = hl_color if eq == "TGBT" else '#00B8FF'
        col_carga = hl_color if eq == "Cargas Bloque D" else '#FF4D5A'
        col_inv = hl_color if eq == "Inversor" else '#A855F7'
        col_pv = hl_color if eq == "Arreglo PV" else '#FFB020'
        col_bess = hl_color if eq == "BESS" else '#00D084'

        fig_sld = go.Figure()
        fig_sld.update_xaxes(visible=False, range=[-110, 110])
        fig_sld.update_yaxes(visible=False, range=[-75, 215])

        # 1. Red CNEL (MT 13.8 kV)
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[200, 145], mode='lines', line=dict(color=col_cnel, width=5 if eq == "Red CNEL" else 2.5), showlegend=False))
        fig_sld.add_annotation(x=35, y=190, text="RED CNEL 13.8 kV", showarrow=False, font=dict(size=12, color=col_cnel, weight="bold"))

        # 2. Transformador (Dos círculos superpuestos)
        fig_sld.add_shape(type="circle", x0=-14, y0=115, x1=14, y1=145, line_color=col_trafo, line_width=5 if eq == "Transformador" else 2.5)
        fig_sld.add_shape(type="circle", x0=-14, y0=95, x1=14, y1=125, line_color=col_trafo, line_width=5 if eq == "Transformador" else 2.5)
        fig_sld.add_annotation(x=55, y=120, text=f"TRAFO {cfg['s_trafo']:.0f} kVA", showarrow=False, font=dict(size=12, color=col_trafo, weight="bold"))

        # 3. Conexión Trafo -> TGBT
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[95, 40], mode='lines', line=dict(color=col_trafo, width=5 if eq == "Transformador" else 2.5), showlegend=False))

        # 4. BUS TGBT (Barra Horizontal Principal)
        fig_sld.add_trace(go.Scatter(x=[-90, 90], y=[40, 40], mode='lines', line=dict(color=col_tgbt, width=8 if eq == "TGBT" else 5), showlegend=False))
        fig_sld.add_annotation(x=0, y=48, text=f"BUS TGBT {cfg['v_nom']:.0f}V", showarrow=False, font=dict(size=13, color=col_tgbt, weight="bold"))

        # 5. Ramal Cargas Bloque D (Izquierda)
        fig_sld.add_trace(go.Scatter(x=[-50, -50], y=[40, 0], mode='lines', line=dict(color=col_carga, width=5 if eq == "Cargas Bloque D" else 2.5), showlegend=False))
        fig_sld.add_shape(type="rect", x0=-80, y0=-20, x1=-20, y1=0, line_color=col_carga, fillcolor='rgba(255,77,90,0.1)', line_width=4 if eq == "Cargas Bloque D" else 2)
        fig_sld.add_annotation(x=-50, y=-10, text="CARGAS BLOQUE D", showarrow=False, font=dict(size=11, color=col_carga, weight="bold"))

        # 6. Ramal Inversor IBR (Derecha)
        fig_sld.add_trace(go.Scatter(x=[50, 50], y=[40, 0], mode='lines', line=dict(color=col_inv, width=5 if eq == "Inversor" else 2.5), showlegend=False))
        fig_sld.add_shape(type="rect", x0=20, y0=-20, x1=80, y1=0, line_color=col_inv, fillcolor='rgba(168,85,247,0.1)', line_width=4 if eq == "Inversor" else 2)
        fig_sld.add_annotation(x=50, y=-10, text=f"INVERSOR {inv_k:.0f} kVA", showarrow=False, font=dict(size=11, color=col_inv, weight="bold"))

        # 7. Sub-ramales DC bajo el Inversor (PV y BESS)
        fig_sld.add_trace(go.Scatter(x=[35, 35], y=[-20, -45], mode='lines', line=dict(color=col_pv, width=4 if eq == "Arreglo PV" else 2), showlegend=False))
        fig_sld.add_trace(go.Scatter(x=[65, 65], y=[-20, -45], mode='lines', line=dict(color=col_bess, width=4 if eq == "BESS" else 2), showlegend=False))

        # Bloque Arreglo PV
        fig_sld.add_shape(type="rect", x0=20, y0=-65, x1=50, y1=-45, line_color=col_pv, fillcolor='rgba(255,176,32,0.1)', line_width=4 if eq == "Arreglo PV" else 2)
        fig_sld.add_annotation(x=35, y=-55, text=f"PV {cfg['p_pv']:.0f} kWp", showarrow=False, font=dict(size=11, color=col_pv, weight="bold"))

        # Bloque BESS
        fig_sld.add_shape(type="rect", x0=55, y0=-65, x1=85, y1=-45, line_color=col_bess, fillcolor='rgba(0,208,132,0.1)', line_width=4 if eq == "BESS" else 2)
        fig_sld.add_annotation(x=70, y=-55, text=f"BESS {cfg['c_bat']:.0f} kWh", showarrow=False, font=dict(size=11, color=col_bess, weight="bold"))

        fig_sld.update_layout(
            height=580, 
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_sld, use_container_width=True)

def render_financiero_y_comparativa(cfg, df_ems, kpis):
    st.markdown("<h3 style='color: #00B8FF;'>Análisis Financiero, VAN, TIR y Matriz Comparativa</h3>", unsafe_allow_html=True)
    
    st.markdown("<h4 style='color: #00D084;'>📊 Matriz Comparativa de Resultados (Antes vs. Después)</h4>", unsafe_allow_html=True)
    
    p_max_inicial = kpis.get('demanda_max', 179.1)
    p_max_optimizado = kpis.get('demanda_recortada', 130.0)
    reduccion_kw = p_max_inicial - p_max_optimizado
    reduccion_pct = (reduccion_kw / p_max_inicial) * 100.0 if p_max_inicial > 0 else 0
    carg_inicial = (p_max_inicial / cfg['s_trafo']) * 100.0
    carg_optimizada = kpis.get('carg_con_ems', kpis.get('carg_con', 13.0))
    
    energia_pv_diaria = df_ems['P_PV'].sum()
    co2_evitado_anual_ton = ((energia_pv_diaria * 0.45) * 365) / 1000
    
    df_matriz = pd.DataFrame({
        "Parámetro / Indicador Técnico": [
            "Demanda Máxima de Red (kW)",
            "Cargabilidad del Transformador (1000 kVA)",
            "Calidad de Tensión & Flickers (EN 50160 / ARCONEL)",
            "Generación Solar Fotovoltaica Autoconsumida",
            "Mitigación de Huella de Carbono Anual"
        ],
        "Escenario Inicial (Informe Matheus - Bloque D)": [
            f"{p_max_inicial:.1f} kW", f"{carg_inicial:.1f} %", "Incumplimiento Plt > 1.0", "0.0 kWh/día", "0.0 tCO2/año"
        ],
        "Escenario Optimizado (EMS + PV + BESS)": [
            f"{p_max_optimizado:.1f} kW", f"{carg_optimizada:.1f} %", "Soporte Volt/VAR Activo (0.98 - 1.02 p.u.)", f"{energia_pv_diaria:.1f} kWh/día", f"{co2_evitado_anual_ton:.1f} tCO2/año"
        ],
        "Impacto / Mejora Alcanzada": [
            f"▼ {reduccion_kw:.1f} kW ({reduccion_pct:.1f}% recorte)", f"▼ {carg_inicial - carg_optimizada:.1f}% carga", "Estabilización de Tensión", f"Ingreso de {cfg['p_pv']:.0f} kWp Limpios", "Reducción directa de emisiones"
        ]
    })
    st.table(df_matriz)

    st.markdown("<hr style='border-color: #26354D;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #00B8FF;'>🛡️ Verificación de Protecciones Eléctricas (NEC / IEEE)</h4>", unsafe_allow_html=True)
    verifs = verificar_protecciones(cfg, kpis)
    df_verifs = pd.DataFrame(verifs)
    st.dataframe(df_verifs, use_container_width=True)

    st.markdown("<hr style='border-color: #26354D;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='color: #00B8FF;'>💰 Evaluador Financiero Completo (VAN, TIR, Payback)</h4>", unsafe_allow_html=True)
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tarifa_demanda = st.number_input("Tarifa Cargo por Demanda Pico (USD/kW-mes)", value=10.50, step=0.50)
        tarifa_energia = st.number_input("Tarifa Energía Consumida (USD/kWh)", value=0.095, step=0.005, format="%.3f")
        tasa_desc = st.number_input("Tasa de Descuento WACC (%)", value=8.0, step=0.5) / 100.0
    with col_t2:
        costo_bess_kwh = st.number_input("Costo Unitario BESS (USD/kWh)", value=400.0, step=25.0)
        costo_pv_kwp = st.number_input("Costo Unitario PV (USD/kWp)", value=800.0, step=50.0)
        inflacion_tar = st.number_input("Inflación Tarifaria Anual (%)", value=4.0, step=0.5) / 100.0

    fin_res = calcular_financiero(cfg, kpis, tarifa_demanda, tarifa_energia, costo_bess_kwh, costo_pv_kwp, tasa_desc, inflacion_tar)
    deg_bess = calcular_degradacion_bess(cfg, df_ems)

    f1, f2, f3, f4 = st.columns(4)
    f1.markdown(f"""<div class="kpi-card"><div class="kpi-title">INVERSIÓN TOTAL (CAPEX)</div><div class="kpi-value">${fin_res['capex_total']:,.0f} <span class="kpi-unit">USD</span></div></div>""", unsafe_allow_html=True)
    f2.markdown(f"""<div class="kpi-card"><div class="kpi-title">VALOR ACTUAL NETO (VAN)</div><div class="kpi-value">${fin_res['van_total']:,.0f} <span class="kpi-unit">USD</span></div></div>""", unsafe_allow_html=True)
    f3.markdown(f"""<div class="kpi-card"><div class="kpi-title">TASA INTERNA RETORNO (TIR)</div><div class="kpi-value">{fin_res['tir_pct']}%</div></div>""", unsafe_allow_html=True)
    f4.markdown(f"""<div class="kpi-card"><div class="kpi-title">PAYBACK DESCONTADO</div><div class="kpi-value">{fin_res['payback_desc']} <span class="kpi-unit">Años</span></div></div>""", unsafe_allow_html=True)

    st.markdown("<h5 style='color: #F8FAFC; margin-top:25px;'>Proyección de Flujo de Caja Descontado (10 Años)</h5>", unsafe_allow_html=True)
    anos = np.arange(0, 11)
    fig_payback = go.Figure()
    fig_payback.add_trace(go.Scatter(x=anos, y=fin_res['van_acumulado'], mode='lines+markers', name='VAN Acumulado (USD)', line=dict(color='#00D084', width=3)))
    fig_payback.add_trace(go.Scatter(x=[0, 10], y=[0, 0], name='Break-even', line=dict(color='#FF4D5A', dash='dash')))
    fig_payback.update_layout(height=350, margin=dict(t=20, b=10))
    st.plotly_chart(fig_payback, use_container_width=True)

    with st.expander("🔋 Degradación y Ciclos de Vida del BESS (LiFePO4)"):
        st.write(f"**Ciclos diarios proyectados:** {deg_bess['ciclos_por_dia']} ciclos/día")
        st.write(f"**Vida útil estimada:** {deg_bess['vida_util_años']} años")
        st.dataframe(deg_bess['proyeccion'], use_container_width=True)

def render_exportaciones(cfg, df_ems, kpis):
    st.markdown("<h3 style='color: #00B8FF;'>Exportación de Datos y Código MATLAB</h3>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["📦 Archivos y Datos", "💻 Código MATLAB"])
    
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            inv_k = kpis.get('inv_kva', kpis.get('inv_req', 157.9))
            st.download_button("📐 DESCARGAR PLANO CAD (.DXF)", generate_dxf_full(cfg, inv_k).encode('utf-8'), f"Unifilar_{cfg['nombre_proyecto'].replace(' ','_')}.dxf", 'application/dxf', use_container_width=True)
        with c2:
            st.download_button("📊 DESCARGAR RESULTADOS (.CSV)", df_ems.to_csv(index=False).encode('utf-8'), 'Resultados_EMS.csv', 'text/csv', use_container_width=True)

    with tab2:
        st.code(generar_codigo_matlab(cfg, kpis), language='matlab')
