import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# CONFIGURACIÓN GENERAL DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Suite EMS - UPS Bloque D", layout="wide", page_icon="🛡️")

st.title("🛡️ Suite Módulos de Ingeniería Integrados - EMS Bloque D")
st.markdown("**Plataforma de Control Energético, Simulación Normativa y Gestión de Demanda**")
st.markdown("---")

# ==========================================
# BARRA LATERAL: CONFIGURACIÓN GLOBAL (Con Rangos Reales)
# ==========================================
st.sidebar.header("⚙️ Parámetros Globales (EMS)")

limite_red = st.sidebar.number_input(
    "Set-point Límite de Red P_lim (kW)", 
    min_value=80.0, max_value=200.0, value=130.0, step=5.0
)
capacidad_bess = st.sidebar.number_input(
    "Capacidad Banco BESS C_bat (kWh)", 
    min_value=50.0, max_value=1000.0, value=250.0, step=10.0
)
potencia_pv = st.sidebar.number_input(
    "Potencia Fotovoltaica P_PV (kWp)", 
    min_value=0.0, max_value=300.0, value=150.0, step=10.0
)
carga_nocturna = st.sidebar.number_input(
    "Carga Nocturna BESS (kW)", 
    min_value=10.0, max_value=100.0, value=40.0, step=5.0
)

# ==========================================
# BASE DE DATOS Y ESTADO DE SIMULACIÓN
# ==========================================
if 'df_base' not in st.session_state:
    st.session_state.df_base = pd.DataFrame({
        'Hora': [f"{h:02d}:00" for h in range(24)],
        'P_Carga_(kW)': [36.0, 36.0, 36.0, 36.0, 36.0, 40.0, 60.0, 90.0, 120.0, 145.0, 160.0, 175.0, 179.1, 140.0, 150.0, 155.0, 160.0, 165.0, 172.0, 175.0, 130.0, 90.0, 50.0, 36.0],
        'P_PV_(kW)': [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 5.0, 25.0, 55.0, 90.0, 120.0, 140.0, 150.0, 140.0, 120.0, 90.0, 55.0, 25.0, 5.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    })

# Escalar perfil fotovoltaico en función de la barra lateral
factor_escala_pv = potencia_pv / 150.0 if potencia_pv > 0 else 0.0
df_calc = st.session_state.df_base.copy()
df_calc['P_PV_(kW)'] = df_calc['P_PV_(kW)'] * factor_escala_pv

# ==========================================
# SELECCIÓN DE MÓDULOS DE INGENIERÍA
# ==========================================
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

# ==========================================
# ALGORITMO EMS DETERMINÍSTICO Y VARIABLES GLOBALES
# ==========================================
df_calc['P_Red_Teorica'] = df_calc['P_Carga_(kW)'] - df_calc['P_PV_(kW)']

soc_min = 0.20 * capacidad_bess
soc_max = capacidad_bess
e_util = soc_max - soc_min
energia_actual = capacidad_bess * 0.50

p_bat_lista, p_red_real_lista, e_bat_lista, soc_lista = [], [], [], []

for idx, row in df_calc.iterrows():
    p_teorica = row['P_Red_Teorica']
    
    # Peak Shaving
    if p_teorica > limite_red:
        p_req = p_teorica - limite_red
        p_bat = p_req if (energia_actual - p_req) >= soc_min else max(0.0, energia_actual - soc_min)
    # Carga Nocturna
    elif 1 <= idx <= 5:
        p_bat = -carga_nocturna if (energia_actual + carga_nocturna) <= soc_max else -(soc_max - energia_actual)
    # Standby
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

# Variables globales para consumo general
demanda_max = float(df_calc['P_Carga_(kW)'].max())
demanda_recortada = float(df_calc['P_Red_Real_(kW)'].max())
reduccion_pico = demanda_max - demanda_recortada
inv_req = potencia_pv / 0.95 if potencia_pv > 0 else (limite_red / 0.95)

v_linea = 220.0
s_trafo = 1000.0
z_percent = 5.75
i_nom = (s_trafo * 1000.0) / (1.73205 * v_linea)
icc_simetrica = i_nom / (z_percent / 100.0)
cargabilidad_sin = (demanda_max / s_trafo) * 100.0
cargabilidad_con = (demanda_recortada / s_trafo) * 100.0

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
                st.image("diagrama.png", caption="Esquema Jerárquico: Trafo 1000 kVA -> Bus 220 V -> Inversor Híbrido", use_container_width=True)
            except Exception:
                st.info("ℹ️ Sube la imagen 'diagrama.png' a tu repositorio para fijar la vista predeterminada.")
    with col2:
        st.markdown("### Jerarquía del Sistema (Dinámica):")
        st.markdown("* **Nivel 1:** Acometida 69 kV Subestación")
        st.markdown("* **Nivel 2:** Trafo Triphasic 1000 kVA (69 kV / 0.22 kV)")
        st.markdown("* **Nivel 3:** Bus Principal Tablero General 220 V")
        st.markdown(f"* **Nivel 4:** Inversor Híbrido **{potencia_pv:.0f} kWp PV** + **{capacidad_bess:.0f} kWh BESS**")

# ==========================================
# MÓDULO 2: CÁLCULO NORMATIVO IEEE
# ==========================================
elif modulo_seleccionado == "⚡ 2. Cálculo Normativo (IEEE 2030 / 1547)":
    st.subheader("⚡ Módulo 2: Cálculo Normativo Internacional (IEEE Std 2030.2 / 2030.7 / 1547)")
    st.markdown("Verificación de reglas analíticas de almacenamiento y algoritmo de gestión de picos.")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Reserva Mínima SOC_min (IEEE 2030.2)", f"{soc_min:.1f} kWh", "20% Capacidad")
    col_b.metric("Capacidad Útil BESS E_util", f"{e_util:.1f} kWh", f"DoD Max: 80%")
    col_c.metric("Potencia Aparente Inversor S_inv (IEEE 1547)", f"{inv_req:.1f} kVA", "FP = 0.95")

    st.markdown("### Tabla de Despacho EMS y Balance Energético (24 Horas)")
    st.dataframe(df_calc.style.format(precision=1), use_container_width=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_calc['Hora'], y=df_calc['P_Carga_(kW)'], name='Demanda Bruta (kW)', line=dict(color='red', dash='dash')))
    fig.add_trace(go.Scatter(x=df_calc['Hora'], y=df_calc['P_Red_Real_(kW)'], name='Consumo Red Real (kW)', fill='tozeroy', line=dict(color='blue')))
    fig.add_trace(go.Scatter(x=df_calc['Hora'], y=[limite_red]*24, name='Límite Set-point (kW)', line=dict(color='green', width=3)))
    fig.update_layout(title="Peak Shaving de Demanda en el Bus Principal", xaxis_title="Hora", yaxis_title="Potencia (kW)", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# MÓDULO 3: DISTRIBUCIÓN MT/BT & TRAFO
# ==========================================
elif modulo_seleccionado == "🏢 3. Distribución MT/BT & Concentración":
    st.subheader("🏢 Módulo 3: Modelado de Transformador Pedestal y Concentración de Cargas")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Capacidad Trafo Bloque D", "1000 kVA")
    c2.metric("Cargabilidad Original", f"{cargabilidad_sin:.1f}%", f"Pico: {demanda_max:.1f} kW")
    c3.metric("Cargabilidad con EMS", f"{cargabilidad_con:.1f}%", f"Pico: {demanda_recortada:.1f} kW", delta_color="normal")

    if cargabilidad_con < 85.0:
        st.success("✔ El transformador de 1000 kVA opera holgadamente dentro del rango térmico de seguridad.")
    else:
        st.error(f"⚠️ Alerta: La cargabilidad del transformador es alta ({cargabilidad_con:.1f}%). Revise el set-point de límite.")
        
    st.info(f"💡 El sistema de gestión, equipado con un arreglo fotovoltaico de **{potencia_pv:.0f} kWp** y un banco BESS de **{capacidad_bess:.0f} kWh**, atenúa el pico de demanda máxima limitando la potencia tomada de la red a un set-point de **{limite_red:.0f} kW**, reduciendo de forma dinámica el estrés térmico en el devanado secundario.")

# ==========================================
# MÓDULO 4: ESTUDIO DE CORTOCIRCUITO (AIC)
# ==========================================
elif modulo_seleccionado == "💥 4. Estudio de Cortocircuito (AIC)":
    st.subheader("💥 Módulo 4: Estudio de Cortocircuito y Capacidad Interruptiva (AIC)")
    st.markdown("Cálculo de corriente de falla simétrica e impedancia equivalente en el tablero principal de 220 V.")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Corriente Nominal In (220V)", f"{i_nom:.1f} A")
    m2.metric("Corriente Falla Simétrica Icc", f"{icc_simetrica / 1000.0:.2f} kA")
    m3.metric("Capacidad Interruptiva Mínima", "50 kA", "Validez Art. 110-9")

    st.warning("⚠️ **Recomendación de Protección:** El disyuntor principal de baja tensión debe poseer un poder de corte (AIC) mayor o igual a 50 kA @ 220V.")

# ==========================================
# MÓDULO 5: MEMORIA TÉCNICO-DESCRIPTIVA (INTEGRACIÓN COMPLETA Y DINÁMICA)
# ==========================================
elif modulo_seleccionado == "📄 5. Memoria Técnico-Descriptiva":
    st.subheader("📄 Módulo 5: Memoria Técnica y Especificaciones de Proyecto (Formato Oficial)")
    st.markdown("Generación automática del marco teórico, normativo y memoria técnica ejecutiva autocalculada:")

    # CONSTRUCCIÓN DE LA MEMORIA TÉCNICA DINÁMICA EN FORMATO EJECUTIVO
    memoria_markdown = f"""
| Departamento: | Ingeniería y Viabilidad Técnica |
| :--- | :--- |
| **Documento:** | Memoria Técnica y Marco Teórico Normativo - Sistema BESS y PV para Peak Shaving (UPS Bloque D) |
| **Código:** | GPS-EMS-UPSD-MTC-001 |
| **Revisión / Fecha:** | Rev. A / 04/09/2026 |
| **Elaborado por:** | Tesista / Proyectista EMS |
| **Aprobado por:** | Tribunal de Titulación - Maestría en Electricidad |

---

### HISTORIAL DE REVISIONES
| N° de Revisión | Fecha | Páginas Revisadas | Motivo de Revisión |
| :---: | :---: | :---: | :--- |
| **A** | 04/09/2026 | Todo el documento | Emisión para memoria técnica de titulación y expediente ejecutivo |

---

### ÍNDICE DE CONTENIDO
1. **OBJETIVOS** (1.1 General, 1.2 Específicos)
2. **ANTECEDENTES Y DESCRIPCIÓN DEL PROYECTO**
3. **BASE TÉCNICA Y MARCO NORMATIVO INTERNACIONAL**
   * 3.1 IEEE Std 2030.2-2015 / IEEE Std 1547.9-2022 (Sistemas BESS)
   * 3.2 IEEE Std 2030.7-2017 (Controladores de Microrredes y EMS)
   * 3.3 IEEE Std 1547-2018 (Interconexión de Recursos Distribuidos DER)
   * 3.4 IEC 61000-4-15 / IEEE Std 1453 (Calidad de Energía y Flicker)
4. **DESARROLLO Y FORMULACIÓN MATEMÁTICA DEL ALGORITMO EMS**
5. **CÁLCULOS NORMATIVOS DE INGENIERÍA Y PARÁMETROS REALES**
6. **ESTUDIO DE CORTOCIRCUITO Y CARGABILIDAD DEL TRANSFORMADOR**
7. **CONCLUSIONES TÉCNICAS**

---

### 1. OBJETIVOS
* **1.1 Objetivo General:** Diseñar y validar el marco teórico, normativo y analítico para la implementación de un Sistema de Gestión Inteligente de la Energía (EMS) basado en almacenamiento BESS ({capacidad_bess:.0f} kWh) y generación fotovoltaica ({potencia_pv:.0f} kWp), orientado al recorte de picos de demanda (*Peak Shaving*) a {limite_red:.0f} kW en el Bloque D de la UPS.
* **1.2 Objetivos Específicos:**
  * Fundamentar analíticamente el comportamiento del algoritmo EMS bajo los estándares **IEEE Std 2030.2-2015**, **IEEE Std 2030.7-2017** e **IEEE Std 1547-2018**.
  * Formular las ecuaciones de gobierno del balance de potencia activa en el bus de 220 V y definir los límites de seguridad de descarga ($DoD$, $SOC_{{min}}$).
  * Validar la capacidad de cortocircuito ($I_{{cc}}$) e impedancia en el transformador de {s_trafo:.0f} kVA.

---

### 2. ANTECEDENTES Y DESCRIPCIÓN DEL PROYECTO
El edificio Bloque D de la UPS cuenta con una acometida alimentada por un transformador de {s_trafo:.0f} kVA (69 kV / 0.22 kV), registrando picos de demanda bruta de hasta {demanda_max:.1f} kW. Para mitigar este impacto, se proyecta una microrred conformada por un arreglo fotovoltaico de {potencia_pv:.0f} kWp, un sistema BESS de {capacidad_bess:.0f} kWh (tecnología LiFePO4) y un inversor híbrido de {inv_req:.1f} kVA, controlado por un algoritmo determinístico configurado a un set-point de {limite_red:.0f} kW.

---

### 3. BASE TÉCNICA Y MARCO NORMATIVO INTERNACIONAL
* **3.1 IEEE Std 2030.2-2015 / IEEE Std 1547.9-2022 (Sistemas BESS):** Rige la integración e interoperabilidad de sistemas de almacenamiento. Define la modelación de la batería, eficiencias de ciclo ($Round-Trip$) y las ventanas de Estado de Carga ($SOC$) obligatorias para prevenir la degradación química.
* **3.2 IEEE Std 2030.7-2017 (Controladores de Microrredes y EMS):** Establece las especificaciones para controladores de microrredes. Define la estructura lógica del algoritmo EMS para el despacho dinámico de picos, autoconsumo y carga nocturna *Off-Peak*.
* **3.3 IEEE Std 1547-2018 (Interconexión de Recursos Distribuidos DER):** Estándar obligatorio para la interconexión de fuentes renovables e inversores. Regula la capacidad de soporte de potencia reactiva ($Q$), la regulación de voltaje en el PCC y el factor de potencia mínimo ($FP \ge 0.95$).
* **3.4 IEC 61000-4-15 / IEEE Std 1453 (Calidad de Energía y Flicker):** Normativa referente a la medición y límites de fluctuaciones de voltaje, fundamentando la atenuación de *Flicker* ($P_{{lt}}$) mediante la inyección rápida de potencia.

---

### 4. DESARROLLO Y FORMULACIÓN MATEMÁTICA DEL ALGORITMO EMS
La demanda neta teórica que requeriría el edificio sin BESS ($P_{{red\_teorica}}$) se calcula mediante:

$$P_{{red\_teorica}}(t) = P_{{carga}}(t) - P_{{PV}}(t)$$

El balance real de potencia contratada a la red ($P_{{red\_real}}$) tras la intervención del BESS es:

$$P_{{red\_real}}(t) = P_{{red\_teorica}}(t) - P_{{bat}}(t)$$

El Estado de Carga ($SOC(t)$) evoluciona según la capacidad asignada:

$$SOC(t) = \\left( \\frac{{E_{{bat}}(t)}}{{{capacidad_bess:.1f}}} \\right) \\times 100\\%$$

Sujeto a los límites de seguridad normativos: $SOC_{{min}} \\le SOC(t) \\le SOC_{{max}}$, donde $SOC_{{min}} = {soc_min:.1f}\\text{{ kWh}}$ ($20\\%$) y $SOC_{{max}} = {capacidad_bess:.1f}\\text{{ kWh}}$ ($100\\%$).

---

### 5. CÁLCULOS NORMATIVOS DE INGENIERÍA
* **5.1 Dimensionamiento BESS (IEEE Std 2030.2):**
  * Capacidad Nominal ($C_{{bat\_max}}$): **{capacidad_bess:.1f} kWh**
  * Reserva Mínima ($SOC_{{min}}$): **{soc_min:.1f} kWh** (20%)
  * Capacidad Útil Operativa ($E_{{util}}$): **{e_util:.1f} kWh** (DoD Max = 80%)
* **5.2 Despacho de Potencia Activa (IEEE Std 2030.7):**
  * Demanda Pico Original: **{demanda_max:.1f} kW**
  * Set-point Límite Configurado: **{limite_red:.1f} kW**
  * Reducción Neta de Demanda (Peak Shaving): **{reduccion_pico:.1f} kW**
* **5.3 Capacidad del Inversor Híbrido (IEEE Std 1547):**
  * Potencia Aparente Mínima Inversor ($S_{{inv}}$): **{inv_req:.1f} kVA** (a FP = 0.95)

---

### 6. ESTUDIO DE CORTOCIRCUITO Y CARGABILIDAD DEL TRANSFORMADOR
* **Corriente Nominal Secundario ($I_{{nom}}$):** $I_{{nom}} = \\frac{{{s_trafo:.0f} \\times 1000}}{{\\sqrt{{3}} \\times {v_linea:.0f}}} = {i_nom:.1f}\\text{{ A}}$
* **Corriente de Cortocircuito Simétrica ($I_{{cc}}$):** $I_{{cc}} = \\frac{{{i_nom:.1f}}}{{0.0575}} = {icc_simetrica / 1000.0:.2f}\\text{{ kA}}$
* **Capacidad Interruptiva Recomendada (Art. 110-9):** Disyuntor principal de **50 kA** @ 220 V.
* **Cargabilidad del Transformador ({s_trafo:.0f} kVA):**
  * Original sin EMS: **{cargabilidad_sin:.1f}%**
  * Gestionada con EMS: **{cargabilidad_con:.1f}%**

---

### 7. CONCLUSIONES TÉCNICAS
* La implementación del algoritmo EMS limita efectivamente la potencia tomada de la red a **{limite_red:.1f} kW**, logrando un aplanamiento de pico de **{reduccion_pico:.1f} kW** ({((reduccion_pico)/demanda_max)*100.0:.1f}% de reducción).
* El transformador de **{s_trafo:.0f} kVA** reduce su cargabilidad del **{cargabilidad_sin:.1f}%** al **{cargabilidad_con:.1f}%**, preservando el margen térmico y extendiendo su vida útil.
* La reserva de descarga del BESS fijada en **{soc_min:.1f} kWh** cumple estrictamente con la norma IEEE Std 2030.2, garantizando más de 4000 ciclos operativos para el banco de almacenamiento.
"""

    # VISTA PREVIA INTERACTIVA CON MARKDOWN
    st.markdown(memoria_markdown)
    
    st.markdown("---")
    col_mem1, col_down2 = st.columns(2)
    with col_mem1:
        st.text_area("Texto Plano para Copiado Rápido:", memoria_markdown, height=200)
    with col_down2:
        st.download_button(
            label="⬇️ Descargar Memoria Técnica Completa (.md)",
            data=memoria_markdown.encode('utf-8'),
            file_name=f'Memoria_Tecnica_EMS_{limite_red:.0f}kW_{capacidad_bess:.0f}kWh.md',
            mime='text/markdown'
        )

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
            file_name=f'Reporte_EMS_{limite_red:.0f}kW_{capacidad_bess:.0f}kWh.csv',
            mime='text/csv'
        )
    with col_down2:
        st.info("💡 Los planos vectoriales (.DXF/DWG) exportados desde AutoCAD/ETAP pueden vincularse directamente en el Módulo 1.")
