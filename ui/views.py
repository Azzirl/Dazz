import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
from core.ems_math import simular_evento_transitorio
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

    m1, m2, m3, m4 = st.columns(4)
    reduccion_pico = kpis['demanda_max'] - kpis['demanda_recortada']
    
    m1.markdown(f"""<div class="kpi-card"><div class="kpi-title">DEMANDA RED</div><div class="kpi-value">{kpis['demanda_recortada']:.1f} <span class="kpi-unit">kW</span></div><div class="kpi-sub"><span>Original: {kpis['demanda_max']:.1f} kW</span> <span class="c-cyan">▼ {reduccion_pico:.1f} kW</span></div></div>""", unsafe_allow_html=True)
    m2.markdown(f"""<div class="kpi-card"><div class="kpi-title">ALMACENAMIENTO BESS</div><div class="kpi-value">{cfg['c_bat']:.0f} <span class="kpi-unit">kWh</span></div><div class="kpi-sub"><span>Tecnología: LiFePO4</span> <span class="c-green">SOC Mín {kpis['soc_min']:.0f} kWh</span></div></div>""", unsafe_allow_html=True)
    m3.markdown(f"""<div class="kpi-card"><div class="kpi-title">INVERSOR REQUERIDO</div><div class="kpi-value">{kpis['inv_req']:.0f} <span class="kpi-unit">kVA</span></div><div class="kpi-sub"><span>Capacidad Aparente</span> <span class="c-green">● Volt/VAR Activo</span></div></div>""", unsafe_allow_html=True)
    m4.markdown(f"""<div class="kpi-card"><div class="kpi-title">CARGABILIDAD TRAFO</div><div class="kpi-value">{kpis['carg_con']:.1f} <span class="kpi-unit">%</span></div><div class="kpi-sub"><span>Trafo {cfg['s_trafo']:.0f} kVA</span> <span class="{'c-green' if kpis['carg_con'] < 85 else 'c-red'}">● {'NORMAL' if kpis['carg_con'] < 85 else 'ALERTA'}</span></div></div>""", unsafe_allow_html=True)

    st.markdown("<h3 style='color:#F8FAFC; margin-top:20px; font-size:22px; font-weight:600;'>Monitoreo de Potencia y Generación PV (24h)</h3>", unsafe_allow_html=True)
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
    st.markdown("<h3 style='color: #00B8FF;'>Desglose Matemático del Sistema</h3>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("<p style='color: #00D084; font-weight: bold;'>1. Balance de Potencia y Recorte de Picos (Peak Shaving)</p>", unsafe_allow_html=True)
        
        p_bruta_pico = kpis['demanda_max']
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
        soc_min_kwh = kpis['soc_min']
        
        with st.expander("🔍 Desglose numérico de Reserva de Batería", expanded=True):
            st.latex(r"SOC_{min} = C_{bat\_total} \times \frac{\%SOC_{min}}{100}")
            st.latex(fr"SOC_{{min}} = {c_bat_total:.2f} \times \frac{{20}}{{100}} = \mathbf{{{soc_min_kwh:.2f} \text{{ kWh}}}}")

    with c2:
        st.markdown("<p style='color: #00D084; font-weight: bold;'>3. Capacidad Reactiva Máxima (IEEE 2800)</p>", unsafe_allow_html=True)
        
        p_activa_pico = kpis['demanda_recortada']
        s_inv_val = kpis['inv_req']
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
    st.markdown("<p style='color: #94A3B8;'>Simulación EMT (Electromagnetic Transients) en ventana de 10 segundos, evaluando la respuesta del inversor frente a perturbaciones de red.</p>", unsafe_allow_html=True)
    
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
    
    if evento_seleccionado == "Cortocircuito Trifásico":
        st.info("Diagnóstico: Falla trifásica en t=2.9s. El voltaje cae a 0.16 p.u. durante 100 ms. El sistema de control inyecta potencia reactiva (soporte dinámico) logrando estabilizar la tensión nominal cumpliendo la curva de tolerancia de la IEEE 2800 y ARCONEL-001/24.")
    elif evento_seleccionado == "Cambio de Irradiancia":
        st.info("Diagnóstico: Caída de irradiancia a 0 W/m² en t=2.0s. El inversor ajusta la potencia de salida sin comprometer los límites de voltaje continuo.")
    elif evento_seleccionado == "Variación de Carga":
        st.info("Diagnóstico: Variación abrupta de carga en t=2.0s. Se generan oscilaciones en frecuencia que son amortiguadas por el EMS dentro del margen permisible de 58.8 Hz a 61.2 Hz.")


def render_unifilar(cfg, kpis):
    st.markdown("<h3 style='color: #00B8FF;'>Diagrama Unifilar Jerárquico (Interfaz SCADA)</h3>", unsafe_allow_html=True)
    c_left, c_right = st.columns([1.5, 3.5])
    
    with c_left:
        st.markdown("<p style='font-size:16px; font-weight:700;'>Equipos</p>", unsafe_allow_html=True)
        eq = st.radio("Sel:", ["Transformador", "BESS", "Inversor", "Arreglo PV", "Red CNEL", "TGBT", "Cargas Bloque D"], label_visibility="collapsed")
        
        if eq == "Transformador":
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #FFFFFF;"><h4 style="color:#FFFFFF; margin-top:0;">⚡ TRANSFORMADOR</h4><div style="font-size:14px; line-height:2.0;"><b>Capacidad:</b> {cfg['s_trafo']} kVA<br><b>Tensión:</b> 69 kV / {cfg['v_nom']/1000} kV<br><b>Carga Actual:</b> {kpis['carg_con']:.1f} %<br><span class="c-green">● NORMAL</span></div></div>""", unsafe_allow_html=True)
        elif eq == "BESS":
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #FFFFFF;"><h4 style="color:#FFFFFF; margin-top:0;">🔋 BANCO BESS</h4><div style="font-size:14px; line-height:2.0;"><b>Capacidad:</b> {cfg['c_bat']} kWh<br><b>Tecnología:</b> LiFePO4<br><span class="c-green">● ONLINE</span></div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="kpi-card" style="border-top:3px solid #FFFFFF;"><h4 style="color:#FFFFFF; margin-top:0;">{eq.upper()}</h4><div style="font-size:14px; line-height:2.0;"><span class="c-green">● ESTADO: OPERATIVO</span></div></div>""", unsafe_allow_html=True)

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
        
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[200, 150], mode='lines', line=dict(color=col_cnel, width=5 if eq == "Red CNEL" else 2), showlegend=False))
        fig_sld.add_annotation(x=30, y=190, text="RED CNEL 13.8 kV", showarrow=False, font=dict(size=12, color=col_cnel))
        
        fig_sld.add_shape(type="circle", x0=-12, y0=115, x1=12, y1=145, line_color=col_trafo, line_width=5 if eq == "Transformador" else 2)
        fig_sld.add_shape(type="circle", x0=-12, y0=95, x1=12, y1=125, line_color=col_trafo, line_width=5 if eq == "Transformador" else 2)
        fig_sld.add_annotation(x=45, y=120, text=f"TRAFO {cfg['s_trafo']} kVA", showarrow=False, font=dict(size=12, color=col_trafo))
        
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[95, 60], mode='lines', line=dict(color=col_tgbt, width=5 if eq == "TGBT" else 2), showlegend=False))
        fig_sld.add_trace(go.Scatter(x=[0, 0], y=[60, 40], mode='lines', line=dict(color=col_tgbt, width=5 if eq == "TGBT" else 2), showlegend=False))
        fig_sld.add_trace(go.Scatter(x=[-90, 90], y=[40, 40], mode='lines', line=dict(color=col_tgbt, width=7 if eq == "TGBT" else 4), showlegend=False))
        fig_sld.add_annotation(x=0, y=47, text=f"BUS TGBT {cfg['v_nom']}V", showarrow=False, font=dict(size=13, color=col_tgbt, weight="bold"))
        
        fig_sld.add_trace(go.Scatter(x=[-50, -50], y=[40, 0], mode='lines', line=dict(color=col_carga, width=5 if eq == "Cargas Bloque D" else 2), showlegend=False))
        fig_sld.add_shape(type="rect", x0=-75, y0=-15, x1=-25, y1=0, line_color=col_carga, line_width=5 if eq == "Cargas Bloque D" else 2)
        fig_sld.add_annotation(x=-50, y=-7.5, text="CARGAS", showarrow=False, font=dict(size=11, color=col_carga))
        
        fig_sld.add_trace(go.Scatter(x=[50, 50], y=[40, 0], mode='lines', line=dict(color=col_inv, width=5 if eq == "Inversor" else 2), showlegend=False))
        fig_sld.add_shape(type="rect", x0=20, y0=-15, x1=80, y1=0, line_color=col_inv, line_width=5 if eq == "Inversor" else 2)
        fig_sld.add_annotation(x=50, y=-7.5, text="INVERSOR", showarrow=False, font=dict(size=11, color=col_inv))
        
        fig_sld.add_trace(go.Scatter(x=[35, 35], y=[-15, -40], mode='lines', line=dict(color=col_pv, width=5 if eq == "Arreglo PV" else 2), showlegend=False))
        fig_sld.add_trace(go.Scatter(x=[65, 65], y=[-15, -40], mode='lines', line=dict(color=col_bess, width=5 if eq == "BESS" else 2), showlegend=False))
        fig_sld.add_shape(type="rect", x0=20, y0=-60, x1=50, y1=-40, line_color=col_pv, line_width=5 if eq == "Arreglo PV" else 2)
        fig_sld.add_annotation(x=35, y=-50, text="PV", showarrow=False, font=dict(size=11, color=col_pv))
        fig_sld.add_shape(type="rect", x0=55, y0=-60, x1=85, y1=-40, line_color=col_bess, line_width=5 if eq == "BESS" else 2)
        fig_sld.add_annotation(x=70, y=-50, text="BESS", showarrow=False, font=dict(size=11, color=col_bess))

        fig_sld.update_layout(height=600, margin=dict(l=0, r=0, t=10, b=10))
        st.plotly_chart(fig_sld, use_container_width=True)


def render_exportaciones(cfg, df_ems, kpis):
    st.markdown("<h3 style='color: #00B8FF;'>Exportación de Datos y Código MATLAB</h3>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📦 Archivos y Datos", "💻 Código MATLAB"])
    
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("<div class='kpi-card' style='padding: 20px;'><h4 style='color:#F8FAFC; margin-top:0;'>Plano Vectorial CAD</h4><p style='color:#94A3B8; font-size:13px;'>Genera el diagrama unifilar CAD/DXF.</p></div>", unsafe_allow_html=True)
            st.download_button("📐 DESCARGAR PLANO CAD (.DXF)", generate_dxf_full(cfg, kpis['inv_req']).encode('utf-8'), f"Unifilar_{cfg['nombre_proyecto'].replace(' ','_')}.dxf", 'application/dxf', use_container_width=True)
        with c2:
            st.markdown("<div class='kpi-card' style='padding: 20px;'><h4 style='color:#F8FAFC; margin-top:0;'>Datos Simulación</h4><p style='color:#94A3B8; font-size:13px;'>Balance horario en CSV.</p></div>", unsafe_allow_html=True)
            st.download_button("📊 DESCARGAR RESULTADOS (.CSV)", df_ems.to_csv(index=False).encode('utf-8'), 'Resultados_EMS.csv', 'text/csv', use_container_width=True)

    with tab2:
        st.markdown("<br><h4 style='color: #F8FAFC;'>Algoritmo Operativo EMS</h4>", unsafe_allow_html=True)
        st.markdown("<p style='color: #94A3B8; font-size: 14px;'>Este script reproduce exactamente la simulación actual y arroja los resultados calculados por el sistema.</p>", unsafe_allow_html=True)
        st.code(generar_codigo_matlab(cfg, kpis), language='matlab')
