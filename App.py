import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Configuración general de la página
st.set_page_config(page_title="Suite EMS - UPS Bloque D", layout="wide", page_icon="🛡️")

# Encabezado principal
st.title("🛡️ Suite Módulos de Ingeniería Integrados - EMS Bloque D")
st.markdown("**Plataforma de Control Energético, Simulación Normativa y Gestión de Demanda**")
st.markdown("---")

# BARRA LATERAL: CONFIGURACIÓN GLOBAL
st.sidebar.header("⚙️ Parámetros Globales (EMS)")
limite_red = st.sidebar.number_input("Set-point Límite de Red P_lim (kW)", value=130.0, step=5.0)
capacidad_bess = st.sidebar.number_input("Capacidad Banco BESS C_bat (kWh)", value=250.0, step=10.0)
potencia_pv = st.sidebar.number_input("Potencia Fotovoltaica P_PV (kWp)", value=150.0, step=10.0)
carga_nocturna = st.sidebar.number_input("Carga Nocturna BESS (kW)", value=40.0, step=5.0)

# ESTADO DE DATOS DE SIMULACIÓN
if 'df_base' not in st.session_state:
    st.session_state.df_base = pd.DataFrame({
        'Hora': [f"{h:02d}:00" for h in range(24)],
        'P_Carga_(kW)': [36.0, 36.0, 36.0, 36.0, 36.0, 40.0, 60.0, 90.0, 120.0, 145.0, 160.0, 175.0, 179.1, 140.0, 150.0, 155.0, 160.0, 165.0, 172.0, 175.0, 130.0, 90.0, 50.0, 36.0],
        'P_PV_(kW)': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 5.0, 25.0, 55.0, 90.0, 120.0, 140.0, 150.0, 140.0, 120.0, 90.0, 55.0, 25.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    })

# SELECCIÓN DE LOS 6 MÓDULOS DE INGENIERÍA
modulos = [
    "📐 1. Diagrama Unifilar Jerárquico",
    "⚡ 2. Cálculo Normativo (IEEE 2030 / 1547)",
    "🏢 3. Distribución MT/BT & Concentración",
    "💥 4. Estudio de Cortocircuito (AIC)",
    "📄 5. Memoria Técnico-Descriptiva",
    "💾 6. Exportación CAD & Reportes"
]

modulo_seleccionado = st.radio("Seleccione el Módulo de Trabajo:", modulos, horizontal=True)
st.markdown("---")

# ALGORITMO EMS DETERMINÍSTICO DE CÁLCULO
df_calc = st.session_state.df_base.copy()
df_calc['P_Red_Teorica'] = df_calc['P_Carga_(kW)'] - df_calc['P_PV_(kW)']

soc_min = 0.20 * capacidad_bess
soc_max = capacidad_bess
energia_actual = capacidad_bess * 0.50

p_bat_lista, p_red_real_lista, e_bat_lista, soc_lista = [], [], [], []

for idx, row in df_calc.iterrows():
    p_teorica = row['P_Red_Teorica']
    if p_teorica > limite_red:
        p_req = p_teorica - limite_red
        p_bat = p_req if (energia_actual - p_req) >= soc_min else max(0.0, energia_actual - soc_min)
    elif 1 <= idx <= 5:
        p_bat = -carga_nocturna if (energia_actual + carga_nocturna) <= soc_max else -(soc_max - energia_actual)
    else:
        p_bat = 0.0

    p_red_real = p_teorica - p_bat
    energia_actual -= p_bat
    soc_actual = (energia_actual / capacidad_bess) * 100.0

    p_bat_lista.append(round(p_bat, 2))
    p_red_real_lista.append(round(p_red_real, 2))
    e_bat_lista.append(round(energia_actual, 2))
    soc_lista.append(round(soc_actual, 2))

df_calc['P_Bateria_(kW)'] = p_bat_lista
df_calc['P_Red_Real_(kW)'] = p_red_real_lista
df_calc['Energia_Almacenada_(kWh)'] = e_bat_lista
df_calc['SOC_(%)'] = soc_lista

# ==========================================
# MÓDULO 1: DIAGRAMA UNIFILAR JERÁRQUICO
# ==========================================
if modulo_seleccionado == "📐 1. Diagrama Unifilar Jerárquico":
    st.subheader("📐 Módulo 1: Diagrama Unifilar Jerárquico")
    st.markdown("Generación y visualización del esquema eléctrico jerárquico bajo estándares IEEE/IEC.")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded_diag = st.file_uploader("Sustituir plano en tiempo real (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
        if uploaded_diag is not None:
            st.image(uploaded_diag, caption="Diagrama Unifilar Cargado", use_container_width=True)
        else:
            try:
                st.image("diagrama.png", caption="Esquema Jerárquico: Red 69 kV -> Trafo 1000 kVA -> Bus 220 V -> PV/BESS", use_container_width=True)
            except Exception:
                st.info("ℹ️ Sube la imagen 'diagrama.png' a tu repositorio para fijar la vista predeterminada.")
    with col2:
        st.markdown("### Jerarquía del Sistema:")
        st.markdown("* **Nivel 1 (Red Superior):** Acometida 69 kV Subestación")
        st.markdown("* **Nivel 2 (Transformación):** Trafo Triphasic 1000 kVA (69 kV / 0.22 kV)")
        st.markdown("* **Nivel 3 (Acoplamiento PCC):** Bus Principal Tablero General 220 V")
        st.markdown("* **Nivel 4 (Generación & Almacenamiento):** Inversor Híbrido 150 kWp PV + 250 kWh BESS")

# ==========================================
# MÓDULO 2: CÁLCULO NORMATIVO IEEE
# ==========================================
elif modulo_seleccionado == "⚡ 2. Cálculo Normativo (IEEE 2030 / 1547)":
    st.subheader("⚡ Módulo 2: Cálculo Normativo Internacional (IEEE Std 2030.2 / 2030.7 / 1547)")
    st.markdown("Verificación de reglas analíticas de almacenamiento y algoritmo de gestión de picos.")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Reserva Mínima SOC_min (IEEE 2030.2)", f"{soc_min:.1f} kWh", "20% Capacidad")
    col_b.metric("Capacidad Útil BESS E_util", f"{soc_max - soc_min:.1f} kWh", f"DoD Max: {((soc_max - soc_min)/capacidad_bess)*100:.0f}%")
    col_c.metric("Potencia Aparente Inversor S_inv (IEEE 1547)", f"{potencia_pv / 0.95:.1f} kVA", "FP = 0.95")

    st.markdown("### Tabla de Despacho EMS y Balance Energético (24 Horas)")
    st.dataframe(df_calc.style.format(precision=1), use_container_width=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_calc['Hora'], y=df_calc['P_Carga_(kW)'], name='Demanda Bruta Edificio (kW)', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=df_calc['Hora'], y=df_calc['P_Red_Real_(kW)'], name='Consumo Red Real (kW)', fill='tozeroy', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df_calc['Hora'], y=[limite_red]*24, name='Límite Set-point (kW)', line=dict(color='green', width=3)))
    fig.update_layout(title="Peak Shaving de Demanda en el Bus Principal", xaxis_title="Hora", yaxis_title="Potencia (kW)", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# MÓDULO 3: DISTRIBUCIÓN MT/BT & TRAFO
# ==========================================
elif modulo_seleccionado == "🏢 3. Distribución MT/BT & Concentración":
    st.subheader("🏢 Módulo 3: Modelado de Transformador Pedestal y Concentración de Cargas")
    
    demanda_max = df_calc['P_Carga_(kW)'].max()
    demanda_recortada = df_calc['P_Red_Real_(kW)'].max()
    cargabilidad_sin = (demanda_max / 1000.0) * 100
    cargabilidad_con = (demanda_recortada / 1000.0) * 100
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Capacidad Trafo Bloque D", "1000 kVA")
    c2.metric("Cargabilidad Original", f"{cargabilidad_sin:.1f}%", f"Pico: {demanda_max:.1f} kW")
    c3.metric("Cargabilidad con EMS", f"{cargabilidad_con:.1f}%", f"Pico: {demanda_recortada:.1f} kW", delta_color="normal")

    st.success("✔ El transformador de 1000 kVA opera holgadamente dentro del rango térmico de seguridad.")
    st.info("El sistema FV de 150 kWp y BESS de 250 kWh atenúa los picos de demanda y reduce el estrés térmico en el devanado secundario.")

# ==========================================
# MÓDULO 4: ESTUDIO DE CORTOCIRCUITO (AIC)
# ==========================================
elif modulo_seleccionado == "💥 4. Estudio de Cortocircuito (AIC)":
    st.subheader("💥 Módulo 4: Estudio de Cortocircuito y Capacidad Interruptiva (AIC)")
    st.markdown("Cálculo de corriente de falla simétrica e impedancia equivalente en el tablero principal de 220 V.")
    
    v_linea = 220.0 # Voltios
    s_trafo = 1000.0 # kVA
    z_percent = 5.75 # Impedancia típica
    
    i_nom = (s_trafo * 1000.0) / (1.73205 * v_linea)
    icc_simetrica = i_nom / (z_percent / 100.0)
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Corriente Nominal In (220V)", f"{i_nom:.1f} A")
    m2.metric("Corriente Falla Simétrica Icc", f"{icc_simetrica / 1000.0:.2f} kA")
    m3.metric("Capacidad Interruptiva Mínima", "50 kA", "Validez Art. 110-9")

    st.warning("⚠️ **Recomendación de Protección:** El disyuntor principal de baja tensión debe poseer un poder de corte (AIC) mayor o igual a 50 kA @ 220V.")

# ==========================================
# MÓDULO 5: MEMORIA TÉCNICO-DESCRIPTIVA
# ==========================================
elif modulo_seleccionado == "📄 5. Memoria Técnico-Descriptiva":
    st.subheader("📄 Módulo 5: Memoria Técnico-Descriptiva para Tesis de Maestría")
    
    resumen_texto = f"""
    MEMORIA TÉCNICO-DESCRIPTIVA DE INGENIERÍA
    PROYECTO: Sistema de Gestión Inteligente de Energía (EMS) para el Bloque D - UPS.
    
    1. ALCANCE Y OBJETIVOS:
       Implementación de un algoritmo EMS determinístico para recortar el pico de demanda de 179.1 kW a {limite_red} kW 
       mediante la integración de un generador fotovoltaico de {potencia_pv} kWp y un sistema de almacenamiento BESS de {capacidad_bess} kWh.
       
    2. MARCO NORMATIVO INTERNACIONAL APLICADO:
       - IEEE Std 2030.2-2015 / IEEE Std 1547.9-2022: Criterios de descarga (DoD 80%) y reserva mínima de seguridad (SOC min = {soc_min:.1f} kWh).
       - IEEE Std 2030.7-2017: Reglas del controlador de microrred para el despacho dinámico de potencia activa.
       - IEEE Std 1547-2018: Inversor dimensionado a {potencia_pv / 0.95:.1f} kVA para soporte de potencia reactiva e inyección a la red.
       
    3. RESULTADOS OPERATIVOS:
       - Potencia pico original: {demanda_max} kW
       - Potencia pico gestionada: {df_calc['P_Red_Real_(kW)'].max()} kW
       - Reducción neta de demanda de red: {demanda_max - df_calc['P_Red_Real_(kW)'].max():.1f} kW
    """
    st.text_area("Expediente Ejecutivo Generado:", resumen_texto, height=320)

# ==========================================
# MÓDULO 6: EXPORTACIÓN CAD Y REPORTES
# ==========================================
elif modulo_seleccionado == "💾 6. Exportación CAD & Reportes":
    st.subheader("💾 Módulo 6: Exportación de Expediente Ejecutivo y Reportes")
    st.markdown("Descarga de la memoria de cálculo procesada y reportes de simulación:")
    
    csv_bytes = df_calc.to_csv(index=False).encode('utf-8')
    
    col_down1, col_down2 = st.columns(2)
    with col_down1:
        st.download_button(
            label="⬇️ Descargar Reporte Completo de Resultados (CSV)",
            data=csv_bytes,
            file_name='Reporte_EMS_Peak_Shaving_UPS.csv',
            mime='text/csv'
        )
    with col_down2:
        st.info("💡 Los planos vectoriales (.DXF/DWG) exportados desde AutoCAD/ETAP pueden vincularse directamente en el Módulo 1.")
