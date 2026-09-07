# Reemplaza SOLO esta función dentro de ui/views.py

def render_exportaciones(cfg, df_ems, kpis):
    st.markdown("<h3 style='color: #00B8FF;'>Exportación y Respaldo Matemático</h3>", unsafe_allow_html=True)
    
    # Crear pestañas para organizar la interfaz
    tab1, tab2, tab3 = st.tabs(["📦 Archivos y Datos", "💻 Código MATLAB", "🧮 Fórmulas y Cálculos"])
    
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

    with tab3:
        st.markdown("<br><h4 style='color: #F8FAFC;'>Ecuaciones del Sistema</h4>", unsafe_allow_html=True)
        
        st.markdown("<p style='color: #00B8FF; font-weight: bold;'>1. Balance de Potencia y Peak Shaving</p>", unsafe_allow_html=True)
        st.latex(r"P_{red}(t) = P_{carga}(t) - P_{pv}(t) - P_{bat}(t)")
        st.markdown("<p style='color: #94A3B8; font-size: 14px;'>Si $P_{teorica} > P_{lim}$, la batería inyecta potencia limitando el consumo de red:</p>", unsafe_allow_html=True)
        st.latex(r"P_{bat} = \min(P_{teorica} - P_{lim}, E_{bat} - SOC_{min})")
        
        st.markdown("<p style='color: #00B8FF; font-weight: bold; margin-top: 20px;'>2. Estado de Carga (SOC)</p>", unsafe_allow_html=True)
        st.latex(r"SOC(\%) = \left( \frac{E_{bat\_actual}}{C_{bat\_total}} \right) \times 100")
        
        st.markdown("<p style='color: #00B8FF; font-weight: bold; margin-top: 20px;'>3. Control de Tensión y Reactivos (Volt/VAR - IEEE 2800)</p>", unsafe_allow_html=True)
        st.markdown("<p style='color: #94A3B8; font-size: 14px;'>Reserva dinámica de reactivos según capacidad del inversor y potencia activa en tiempo real:</p>", unsafe_allow_html=True)
        st.latex(r"Q_{max} = \sqrt{S_{inv}^2 - P_{activa}^2}")
        
        st.markdown("<p style='color: #94A3B8; font-size: 14px;'>Compensación por caída de tensión ($V < 0.98 \text{ p.u.}$):</p>", unsafe_allow_html=True)
        st.latex(r"Q_{inyectada} = \min\left[ (0.98 - V_{actual}) \times (S_{inv} \times 2), Q_{max} \right]")
        
        st.markdown("<p style='color: #94A3B8; font-size: 14px;'>Compensación por sobretensión ($V > 1.02 \text{ p.u.}$):</p>", unsafe_allow_html=True)
        st.latex(r"Q_{absorbida} = \max\left[ -(V_{actual} - 1.02) \times (S_{inv} \times 2), -Q_{max} \right]")
