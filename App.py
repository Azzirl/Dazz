import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuración de página
st.set_page_config(page_title="EMS - Peak Shaving UPS Bloque D", layout="wide", page_icon="⚡")

# Título de la aplicación
st.title("⚡ Sistema de Gestión Inteligente de la Energía (EMS) - Peak Shaving")
st.markdown("**Proyecto:** Optimización de demanda eléctrica mediante PV y BESS en el Bloque D de la UPS")
st.markdown("---")

# BARRA LATERAL - PARÁMETROS TÉCNICOS
st.sidebar.header("⚙️ Parámetros de Control (EMS)")
st.sidebar.markdown("Ajuste los set-points operativos del sistema:")

input_limite = st.sidebar.text_input("Set-point Límite de Red $P_{limite}$ (kW)", value="130.0")
input_capacidad = st.sidebar.text_input("Capacidad Banco BESS $C_{bat}$ (kWh)", value="250.0")
input_nocturna = st.sidebar.text_input("Carga Nocturna Programada (kW)", value="40.0")

# Validación numérica de parámetros
try:
    limite_red = float(input_limite)
    capacidad_bess = float(input_capacidad)
    carga_nocturna = float(input_nocturna)
except ValueError:
    st.error("⚠️ Ingrese valores numéricos válidos en los campos de la barra lateral.")
    st.stop()

# Restricciones operativas del BESS
soc_min = 0.20 * capacidad_bess  # Límite mínimo de descarga (20%)
soc_max = capacidad_bess         # Capacidad nominal máxima (100%)

# PESTAÑAS DE NAVEGACIÓN
tab1, tab2, tab3 = st.tabs(["📊 Panel de Control y Cálculos", "📐 Diagrama Unifilar", "📄 Generación de Reportes"])

with tab1:
    st.subheader("1. Configuración del Perfil de Carga")
    
    opcion_origen = st.radio(
        "Seleccione el origen de datos de simulación:",
        ["Perfil Base del Bloque D (24 Horas)", "Cargar Archivo Externo (.csv / .xlsx)"],
        horizontal=True
    )

    if opcion_origen == "Perfil Base del Bloque D (24 Horas)":
        if 'df_base' not in st.session_state:
            st.session_state.df_base = pd.DataFrame({
                'Hora': [f"{h:02d}:00" for h in range(24)],
                'P_Carga_(kW)': [36.0, 36.0, 36.0, 36.0, 36.0, 40.0, 60.0, 90.0, 120.0, 145.0, 160.0, 175.0, 179.1, 140.0, 150.0, 155.0, 160.0, 165.0, 172.0, 175.0, 130.0, 90.0, 50.0, 36.0],
                'P_PV_(kW)': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 5.0, 25.0, 55.0, 90.0, 120.0, 140.0, 150.0, 140.0, 120.0, 90.0, 55.0, 25.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0]
            })
        df_input = st.session_state.df_base
        st.info("Edite las celdas directamente en la tabla si desea probar otros escenarios:")
        df_trabajo = st.data_editor(df_input, use_container_width=True, key="editor_base")
    else:
        archivo_subido = st.file_uploader("Cargue su archivo de perfil de demanda", type=['csv', 'xlsx'])
        if archivo_subido is not None:
            try:
                if archivo_subido.name.endswith('.csv'):
                    df_raw = pd.read_csv(archivo_subido)
                else:
                    df_raw = pd.read_excel(archivo_subido)
                
                # Búsqueda/Mapeo inteligente de columnas
                col_hora = [c for c in df_raw.columns if 'hora' in str(c).lower() or 'time' in str(c).lower()]
                col_carga = [c for c in df_raw.columns if 'carga' in str(c).lower() or 'demanda' in str(c).lower() or 'kw' in str(c).lower()]
                col_pv = [c for c in df_raw.columns if 'pv' in str(c).lower() or 'solar' in str(c).lower()]

                if col_hora and col_carga:
                    df_trabajo = pd.DataFrame()
                    df_trabajo['Hora'] = df_raw[col_hora[0]].astype(str)
                    df_trabajo['P_Carga_(kW)'] = pd.to_numeric(df_raw[col_carga[0]], errors='coerce').fillna(0.0)
                    df_trabajo['P_PV_(kW)'] = pd.to_numeric(df_raw[col_pv[0]], errors='coerce').fillna(0.0) if col_pv else 0.0
                    st.success("Archivo cargado y estructurado correctamente.")
                else:
                    st.warning("⚠️ No se identificaron automáticamente las columnas. Asegúrese de incluir encabezados: 'Hora', 'P_Carga_(kW)', 'P_PV_(kW)'.")
                    df_trabajo = df_raw
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")
                st.stop()
        else:
            st.info("Por favor suba un archivo para continuar.")
            st.stop()

    # EJECUCIÓN DEL ALGORITMO EMS DETERMINÍSTICO
    df_res = df_trabajo.copy()
    df_res['P_Red_Teorica'] = df_res['P_Carga_(kW)'] - df_res['P_PV_(kW)']
    
    p_bat_lista = []
    p_red_real_lista = []
    e_bat_lista = []
    soc_lista = []

    # Estado inicial de batería (50% SOC)
    energia_actual = capacidad_bess * 0.50

    for idx, row in df_res.iterrows():
        # Parsing seguro del valor horario
        try:
            val_h = str(row['Hora']).split(':')[0]
            hora_num = int(val_h)
        except Exception:
            hora_num = idx % 24

        p_teorica = float(row['P_Red_Teorica'])
        
        # Despacho de Potencia (Reglas EMS)
        if p_teorica > limite_red:
            p_bat_req = p_teorica - limite_red
            if (energia_actual - p_bat_req) >= soc_min:
                p_bat = p_bat_req
            else:
                p_bat = max(0.0, energia_actual - soc_min)
        elif 1 <= hora_num <= 5:
            p_bat = -carga_nocturna
            if (energia_actual - p_bat) > soc_max:
                p_bat = -(soc_max - energia_actual)
        else:
            p_bat = 0.0

        p_red_real = p_teorica - p_bat
        energia_actual = energia_actual - p_bat
        soc_actual = (energia_actual / capacidad_bess) * 100.0

        p_bat_lista.append(round(p_bat, 2))
        p_red_real_lista.append(round(p_red_real, 2))
        e_bat_lista.append(round(energia_actual, 2))
        soc_lista.append(round(soc_actual, 2))

    df_res['P_Bateria_(kW)'] = p_bat_lista
    df_res['P_Red_Real_(kW)'] = p_red_real_lista
    df_res['Energia_Almacenada_(kWh)'] = e_bat_lista
    df_res['SOC_(%)'] = soc_lista

    st.markdown("---")
    st.subheader("2. Resultados del Balance de Potencia y BESS")
    st.dataframe(
        df_res[['Hora', 'P_Carga_(kW)', 'P_PV_(kW)', 'P_Red_Teorica', 'P_Bateria_(kW)', 'P_Red_Real_(kW)', 'Energia_Almacenada_(kWh)', 'SOC_(%)']].style.format(precision=1),
        use_container_width=True
    )

    st.subheader("3. Comportamiento Dinámico del Recorte de Picos (Peak Shaving)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_res['Hora'], y=df_res['P_Carga_(kW)'], mode='lines+markers', name='Demanda Bruta Edificio (kW)', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=df_res['Hora'], y=df_res['P_Red_Real_(kW)'], mode='lines+markers', name='Demanda Suministrada por Red (kW)', fill='tozeroy', line=dict(color='#1f77b4')))
    fig.add_trace(go.Scatter(x=df_res['Hora'], y=[limite_red]*len(df_res), mode='lines', name=f'Límite de Red Configurado ({limite_red} kW)', line=dict(color='green', width=3)))
    
    fig.update_layout(
        xaxis_title='Hora del Día',
        yaxis_title='Potencia Activa (kW)',
        template='plotly_white',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    # Gráfica adicional del Estado de Carga (SOC)
    st.subheader("4. Evolución del Estado de Carga del Banco BESS (SOC)")
    fig_soc = go.Figure()
    fig_soc.add_trace(go.Scatter(x=df_res['Hora'], y=df_res['SOC_(%)'], mode='lines+markers', name='SOC (%)', line=dict(color='purple', width=2)))
    fig_soc.update_layout(
        xaxis_title='Hora del Día',
        yaxis_title='Estado de Carga (%)',
        yaxis=dict(range=[0, 105]),
        template='plotly_white'
    )
    st.plotly_chart(fig_soc, use_container_width=True)

with tab2:
    st.subheader("Diagrama Unifilar del Sistema Eléctrico")
    st.markdown("Visualización del esquema de interconexión del Bloque D, Inversor Híbrido, BESS y Red Principal.")
    
    # Intentar cargar imagen local del repositorio o permitir subida rápida
    uploaded_diag = st.file_uploader("Sube una imagen del plano unifilar si deseas sustituir la vista predeterminada", type=['png', 'jpg', 'jpeg'])
    
    if uploaded_diag is not None:
        st.image(uploaded_diag, caption="Diagrama Unifilar del Sistema (Plano Cargado)", use_container_width=True)
    else:
        try:
            st.image("diagrama.png", caption="Diagrama Unifilar Principal - ETAP / AutoCAD", use_container_width=True)
        except Exception:
            st.info("ℹ️ Para mostrar un diagrama fijo por defecto, coloque una imagen con el nombre `diagrama.png` en la raíz de su repositorio GitHub.")

with tab3:
    st.subheader("Generación y Exportación de Reportes Técnicos")
    st.markdown("Descargue la memoria de cálculo del despacho de carga y operación de almacenamiento en formato CSV:")
    
    if 'df_res' in locals():
        csv_data = df_res.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Descargar Reporte Completo de Resultados (CSV)",
            data=csv_data,
            file_name='Reporte_EMS_Peak_Shaving_UPS.csv',
            mime='text/csv',
        )
