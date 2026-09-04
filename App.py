import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuración de la página
st.set_page_config(page_title="EMS - Peak Shaving Fotovoltaico", layout="wide")

# Título principal
st.title("Sistema de Gestión Inteligente de la Energía basado en Peak Shaving")
st.markdown("---")

# 1. DATOS BASE INTERNOS (Perfil de 24 horas del Bloque D)
datos_internos = {
    'Hora': [f"{h}:00" for h in range(24)],
    'P_Carga_(kW)': [36.0, 36.0, 36.0, 36.0, 36.0, 40.0, 60.0, 90.0, 120.0, 145.0, 160.0, 175.0, 179.1, 140.0, 150.0, 155.0, 160.0, 165.0, 172.0, 175.0, 130.0, 90.0, 50.0, 36.0],
    'P_PV_(kW)': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 5.0, 25.0, 55.0, 90.0, 120.0, 140.0, 150.0, 140.0, 120.0, 90.0, 55.0, 25.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0]
}

# BARRA LATERAL (ENTRADA DE TEXTO POR EL USUARIO)
st.sidebar.header("⚙️ Parámetros del Sistema")
st.sidebar.markdown("Ingrese los parámetros de diseño:")

# Campos de entrada como texto
input_limite = st.sidebar.text_input("Límite de Red / Set-point (kW)", value="130.0")
input_capacidad = st.sidebar.text_input("Capacidad BESS (kWh)", value="250.0")
input_nocturna = st.sidebar.text_input("Carga Nocturna BESS (kW)", value="40.0")

# Validación y conversión del texto a número
try:
    limite_red = float(input_limite)
    capacidad_bess = float(input_capacidad)
    carga_nocturna = float(input_nocturna)
except ValueError:
    st.error("⚠️ Por favor ingrese valores numéricos válidos en los campos de texto de la barra lateral.")
    st.stop()

soc_min = 0.20 * capacidad_bess # 20% límite de seguridad
soc_max = capacidad_bess        # 100% capacidad

# PESTAÑAS DE NAVEGACIÓN
tab1, tab2, tab3 = st.tabs(["📊 Panel de Control y Cálculos", "📐 Diagrama Unifilar", "📄 Generación de Reportes"])

with tab1:
    st.subheader("1. Cálculo Automático Interno del Algoritmo EMS")
    
    # Cargar datos internos automáticamente a un DataFrame
    df = pd.DataFrame(datos_internos)

    # Algoritmo de Peak Shaving
    df['P_Red_Teorica'] = df['P_Carga_(kW)'] - df['P_PV_(kW)']
    
    p_bat_lista = []
    p_red_real_lista = []
    e_bat_lista = []
    soc_lista = []

    # Estado inicial de la batería (50%)
    energia_actual = capacidad_bess * 0.5

    for index, row in df.iterrows():
        hora_actual = int(row['Hora'].split(':')[0])
        p_teorica = row['P_Red_Teorica']
        
        # Lógica de Despacho (EMS)
        if p_teorica > limite_red:
            p_bat_req = p_teorica - limite_red
            if (energia_actual - p_bat_req) >= soc_min:
                p_bat = p_bat_req
            else:
                p_bat = max(0.0, energia_actual - soc_min)
        elif 1 <= hora_actual <= 5:
            p_bat = -carga_nocturna
            if (energia_actual - p_bat) > soc_max:
                p_bat = -(soc_max - energia_actual)
        else:
            p_bat = 0.0

        p_red_real = p_teorica - p_bat
        energia_actual = energia_actual - p_bat
        soc_actual = (energia_actual / capacidad_bess) * 100

        p_bat_lista.append(p_bat)
        p_red_real_lista.append(p_red_real)
        e_bat_lista.append(energia_actual)
        soc_lista.append(soc_actual)

    # Agregar resultados al DataFrame
    df['P_Bateria_(kW)'] = p_bat_lista
    df['P_Red_Real_(kW)'] = p_red_real_lista
    df['Energia_Almacenada_(kWh)'] = e_bat_lista
    df['SOC_(%)'] = soc_lista

    # Mostrar tabla de resultados
    st.dataframe(df.style.format(precision=1), use_container_width=True)

    # GRÁFICA INTERACTIVA
    st.subheader("📈 Análisis Gráfico del Recorte de Picos")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Hora'], y=df['P_Carga_(kW)'], mode='lines+markers', name='Demanda del Edificio (kW)', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=df['Hora'], y=df['P_Red_Real_(kW)'], mode='lines+markers', name='Consumo Real de la Red (kW)', fill='tozeroy', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df['Hora'], y=[limite_red]*len(df), mode='lines', name='Límite Configurado (Peak Shaving)', line=dict(color='green', width=3)))
    
    fig.update_layout(title='Comportamiento de la Red vs Demanda Original', xaxis_title='Hora del Día', yaxis_title='Potencia (kW)', template='plotly_white')
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Diagrama Unifilar del Sistema (ETAP / AutoCAD)")
    st.markdown("Cargue el archivo de imagen del plano eléctrico nombrado `diagrama.png` en el repositorio.")
    try:
        st.image("diagrama.png", caption="Diagrama Eléctrico del Bloque D con Sistema Fotovoltaico y BESS", use_container_width=True)
    except Exception:
        st.warning("⚠️ Para visualizar el diagrama aquí, sube una imagen llamada 'diagrama.png' a tu repositorio de GitHub.")

with tab3:
    st.subheader("Generación y Descarga de Reportes")
    st.markdown("Descargue el registro completo con los cálculos de despacho de batería y recortes de demanda.")
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Descargar Reporte de Resultados (CSV)",
        data=csv,
        file_name='Reporte_Peak_Shaving_Resultados.csv',
        mime='text/csv',
    )
