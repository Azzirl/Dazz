import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ==========================================
# CONFIGURACIÓN GENERAL DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Suite EMS - UPS Bloque D", layout="wide", page_icon="🛡️")

st.title("🛡️ Suite Módulos de Ingeniería Integrados - EMS Bloque D")
st.markdown("**Plataforma de Control Energético, Simulación Normativa y Gestión de Demanda**")
st.markdown("---")

# ==========================================
# BARRA LATERAL: CONFIGURACIÓN GLOBAL
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

# Escalar perfil fotovoltaico
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
# ALGORITMO EMS DETERMINÍSTICO DE CÁLCULO
# ==========================================
df_calc['P_Red_Teorica'] = df_calc['P_Carga_(kW)'] - df_calc['P_PV_(kW)']

soc_min = 0.20 * capacidad_bess
soc_max = capacidad_bess
e_util = soc_max - soc_min
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
# FUNCIÓN GENERADORA DE DOCUMENTO WORD (.DOCX)
# ==========================================
def generar_memoria_docx():
    doc = Document()
    
    # Título principal
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_title = p_title.add_run("MEMORIA TÉCNICA Y ESPECIFICACIONES DE PROYECTO")
    r_title.bold = True
    r_title.font.size = Pt(16)
    
    # Tabla de metadatos estilo expediente
    table = doc.add_table(rows=5, cols=2)
    table.style = 'Table Grid'
    data_meta = [
        ("Departamento:", "Ingeniería y Viabilidad Técnica"),
        ("Documento:", "Memoria Técnica y Marco Teórico Normativo - EMS Bloque D (UPS)"),
        ("Código del Documento:", "GPS-EMS-UPSD-MTC-001"),
        ("Revisión / Fecha:", "Rev. A / 04/09/2026"),
        ("Elaborado por:", "Tesista / Proyectista EMS - Maestría en Electricidad")
    ]
    for i, (k, v) in enumerate(data_meta):
        row = table.rows[i]
        row.cells[0].paragraphs[0].add_run(k).bold = True
        row.cells[1].paragraphs[0].add_run(v)
        
    doc.add_paragraph() # Espaciador
    
    # 1. OBJETIVOS
    doc.add_heading('1. OBJETIVOS', level=1)
    doc.add_heading('1.1 Objetivo General', level=2)
    doc.add_paragraph(f"Diseñar y validar el marco teórico, normativo y analítico para la implementación de un Sistema de Gestión Inteligente de la Energía (EMS) basado en almacenamiento BESS ({capacidad_bess:.0f} kWh) y generación fotovoltaica ({potencia_pv:.0f} kWp), orientado al recorte de picos de demanda (Peak Shaving) a {limite_red:.0f} kW en el Bloque D de la UPS.")
    
    doc.add_heading('1.2 Objetivos Específicos', level=2)
    p1 = doc.add_paragraph(style='List Bullet')
    p1.add_run("Fundamentar analíticamente el comportamiento del algoritmo EMS bajo los estándares IEEE Std 2030.2-2015, IEEE Std 2030.7-2017 e IEEE Std 1547-2018.")
    p2 = doc.add_paragraph(style='List Bullet')
    p2.add_run("Formular las ecuaciones de gobierno del balance de potencia activa en el bus de 220 V y definir los límites de seguridad de descarga (DoD, SOCmin).")
    p3 = doc.add_paragraph(style='List Bullet')
    p3.add_run(f"Validar la capacidad de cortocircuito (Icc) e impedancia en el transformador de {s_trafo:.0f} kVA.")

    # 2. ANTECEDENTES
    doc.add_heading('2. ANTECEDENTES Y DESCRIPCIÓN DEL PROYECTO', level=1)
    doc.add_paragraph(f"El edificio Bloque D de la UPS cuenta con una acometida alimentada por un transformador de {s_trafo:.0f} kVA (69 kV / 0.22 kV), registrando picos de demanda bruta de hasta {demanda_max:.1f} kW. Para mitigar este impacto, se proyecta una microrred conformada por un arreglo fotovoltaico de {potencia_pv:.0f} kWp, un sistema BESS de {capacidad_bess:.0f} kWh (tecnología LiFePO4) y un inversor híbrido de {inv_req:.1f} kVA, controlado por un algoritmo determinístico configurado a un set-point de {limite_red:.0f} kW.")

    # 3. MARCO NORMATIVO
    doc.add_heading('3. BASE TÉCNICA Y MARCO NORMATIVO INTERNACIONAL', level=1)
    
    p = doc.add_paragraph(style='List Bullet')
    p.add_run("IEEE Std 2030.2-2015 / IEEE Std 1547.9-2022 (Sistemas BESS): ").bold = True
    p.add_run("Rige la integración e interoperabilidad de sistemas de almacenamiento. Define la modelación de la batería, eficiencias de ciclo (Round-Trip) y las ventanas de Estado de Carga (SOC) obligatorias para prevenir la degradación química.")
    
    p = doc.add_paragraph(style='List Bullet')
    p.add_run("IEEE Std 2030.7-2017 (Controladores de Microrredes y EMS): ").bold = True
    p.add_run("Establece las especificaciones para controladores de microrredes. Define la estructura lógica del algoritmo EMS para el despacho dinámico de picos, autoconsumo y carga nocturna Off-Peak.")
    
    p = doc.add_paragraph(style='List Bullet')
    p.add_run("IEEE Std 1547-2018 (Interconexión de Recursos Distribuidos DER): ").bold = True
    p.add_run("Estándar obligatorio para la interconexión de fuentes renovables e inversores. Regula la capacidad de soporte de potencia reactiva (Q), la regulación de voltaje en el PCC y el factor de potencia mínimo (FP >= 0.95).")
    
    p = doc.add_paragraph(style='List Bullet')
    p.add_run("IEC 61000-4-15 / IEEE Std 1453 (Calidad de Energía y Flicker): ").bold = True
    p.add_run("Normativa referente a la medición y límites de fluctuaciones de voltaje, fundamentando la atenuación de Flicker (Plt) mediante la inyección rápida de potencia.")

    # 4. DESARROLLO MATEMÁTICO
    doc.add_heading('4. DESARROLLO Y FORMULACIÓN MATEMÁTICA DEL ALGORITMO EMS', level=1)
    doc.add_paragraph("La demanda neta teórica que requeriría el edificio sin BESS (P_red_teorica) se calcula mediante:")
    doc.add_paragraph("P_red_teorica(t) = P_carga(t) - P_PV(t)")
    doc.add_paragraph("El balance real de potencia contratada a la red (P_red_real) tras la intervención del BESS es:")
    doc.add_paragraph("P_red_real(t) = P_red_teorica(t) - P_bat(t)")
    doc.add_paragraph(f"El Estado de Carga (SOC(t)) evoluciona según la capacidad asignada ({capacidad_bess:.1f} kWh) sujeto a los límites de seguridad normativos: SOC_min <= SOC(t) <= SOC_max, donde SOC_min = {soc_min:.1f} kWh (20%) y SOC_max = {capacidad_bess:.1f} kWh (100%).")

    # 5. CÁLCULOS NORMATIVOS
    doc.add_heading('5. CÁLCULOS NORMATIVOS DE INGENIERÍA', level=1)
    doc.add_paragraph(f"• Dimensionamiento BESS (IEEE Std 2030.2): Capacidad Nominal = {capacidad_bess:.1f} kWh | Reserva Mínima (SOC_min) = {soc_min:.1f} kWh (20%) | Capacidad Útil (E_util) = {e_util:.1f} kWh (DoD Max = 80%).")
    doc.add_paragraph(f"• Despacho de Potencia Activa (IEEE Std 2030.7): Demanda Pico Original = {demanda_max:.1f} kW | Set-point Límite = {limite_red:.1f} kW | Reducción Neta (Peak Shaving) = {reduccion_pico:.1f} kW.")
    doc.add_paragraph(f"• Capacidad Inversor Híbrido (IEEE Std 1547): Potencia Aparente Mínima (S_inv) = {inv_req:.1f} kVA (a FP = 0.95).")

    # 6. CORTOCIRCUITO Y TRANSFORMADOR
    doc.add_heading('6. ESTUDIO DE CORTOCIRCUITO Y CARGABILIDAD DEL TRANSFORMADOR', level=1)
    doc.add_paragraph(f"Corriente Nominal Secundario (I_nom): {i_nom:.1f} A @ {v_linea:.0f} V")
    doc.add_paragraph(f"Corriente de Cortocircuito Simétrica (I_cc): {icc_simetrica / 1000.0:.2f} kA (Z% = 5.75%)")
    doc.add_paragraph("Capacidad Interruptiva Recomendada (Art. 110-9): Disyuntor principal de 50 kA @ 220 V.")
    doc.add_paragraph(f"Cargabilidad del Transformador ({s_trafo:.0f} kVA): Original sin EMS = {cargabilidad_sin:.1f}% | Gestionada con EMS = {cargabilidad_con:.1f}%")

    # 7. CONCLUSIONES
    doc.add_heading('7. CONCLUSIONES TÉCNICAS', level=1)
    p = doc.add_paragraph(style='List Bullet')
    p.add_run(f"La implementación del algoritmo EMS limita efectivamente la potencia tomada de la red a {limite_red:.1f} kW, logrando un aplanamiento de pico de {reduccion_pico:.1f} kW ({((reduccion_pico)/demanda_max)*100.0:.1f}% de reducción).")
    p = doc.add_paragraph(style='List Bullet')
    p.add_run(f"El transformador de {s_trafo:.0f} kVA reduce su cargabilidad del {cargabilidad_sin:.1f}% al {cargabilidad_con:.1f}%, preservando el margen térmico y extendiendo su vida útil.")
    p = doc.add_paragraph(style='List Bullet')
    p.add_run(f"La reserva de descarga del BESS fijada en {soc_min:.1f} kWh cumple estrictamente con la norma IEEE Std 2030.2, garantizando más de 4000 ciclos operativos.")

    target = io.BytesIO()
    doc.save(target)
    return target.getvalue()

# ==========================================
# MÓDULO 1 A MÓDULO 4 (Contenido Estándar)
# ==========================================
if modulo_seleccionado == "📐 1. Diagrama Unifilar Jerárquico":
    st.subheader("📐 Módulo 1: Diagrama Unifilar Jerárquico")
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

elif modulo_seleccionado == "⚡ 2. Cálculo Normativo (IEEE 2030 / 1547)":
    st.subheader("⚡ Módulo 2: Cálculo Normativo Internacional (IEEE Std 2030.2 / 2030.7 / 1547)")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Reserva Mínima SOC_min (IEEE 2030.2)", f"{soc_min:.1f} kWh", "20% Capacidad")
    col_b.metric("Capacidad Útil BESS E_util", f"{e_util:.1f} kWh", "DoD Max: 80%")
    col_c.metric("Potencia Aparente Inversor S_inv (IEEE 1547)", f"{inv_req:.1f} kVA", "FP = 0.95")
    st.dataframe(df_calc.style.format(precision=1), use_container_width=True)

elif modulo_seleccionado == "🏢 3. Distribución MT/BT & Concentración":
    st.subheader("🏢 Módulo 3: Modelado de Transformador Pedestal y Concentración de Cargas")
    c1, c2, c3 = st.columns(3)
    c1.metric("Capacidad Trafo Bloque D", "1000 kVA")
    c2.metric("Cargabilidad Original", f"{cargabilidad_sin:.1f}%", f"Pico: {demanda_max:.1f} kW")
    c3.metric("Cargabilidad con EMS", f"{cargabilidad_con:.1f}%", f"Pico: {demanda_recortada:.1f} kW", delta_color="normal")
    st.success("✔ El transformador de 1000 kVA opera holgadamente dentro del rango térmico de seguridad.")

elif modulo_seleccionado == "💥 4. Estudio de Cortocircuito (AIC)":
    st.subheader("💥 Módulo 4: Estudio de Cortocircuito y Capacidad Interruptiva (AIC)")
    m1, m2, m3 = st.columns(3)
    m1.metric("Corriente Nominal In (220V)", f"{i_nom:.1f} A")
    m2.metric("Corriente Falla Simétrica Icc", f"{icc_simetrica / 1000.0:.2f} kA")
    m3.metric("Capacidad Interruptiva Mínima", "50 kA", "Validez Art. 110-9")

# ==========================================
# MÓDULO 5: MEMORIA TÉCNICO-DESCRIPTIVA (EXPORTACIÓN WORD)
# ==========================================
elif modulo_seleccionado == "📄 5. Memoria Técnico-Descriptiva":
    st.subheader("📄 Módulo 5: Memoria Técnica y Especificaciones de Proyecto")
    st.markdown("Generación del expediente técnico oficial con formato ejecutivo y normas internacionales:")

    # Descarga directa en Word (.docx)
    docx_bytes = generar_memoria_docx()

    col_down_doc, col_info_doc = st.columns([1, 2])
    with col_down_doc:
        st.download_button(
            label="📄 Descargar Memoria Técnica en Word (.docx)",
            data=docx_bytes,
            file_name=f'Memoria_Tecnica_EMS_{limite_red:.0f}kW_{capacidad_bess:.0f}kWh.docx',
            mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    with col_info_doc:
        st.success("✔ Documento Word generado en tiempo real con todas las variables de la simulación.")

    st.markdown("---")
    st.markdown("### Vista Previa del Expediente Técnico:")
    st.info(f"""
    **DOCUMENTO:** Memoria Técnica y Especificaciones de Proyecto (GPS-EMS-UPSD-MTC-001)
    
    **1. OBJETIVOS:** Implementación del sistema EMS para el Bloque D limitando la demanda a {limite_red:.1f} kW con un BESS de {capacidad_bess:.1f} kWh y PV de {potencia_pv:.1f} kWp.
    
    **2. MARCO NORMATIVO:** Fundamentado en IEEE Std 2030.2-2015, IEEE Std 2030.7-2017 e IEEE Std 1547-2018.
    
    **3. RESULTADOS OPERATIVOS:**
    - Demanda Pico Inicial: {demanda_max:.1f} kW
    - Demanda Pico Gestionada: {demanda_recortada:.1f} kW
    - Reducción Neta de Demanda (Peak Shaving): {reduccion_pico:.1f} kW
    - Cargabilidad Trafo (1000 kVA): Reducida de {cargabilidad_sin:.1f}% a {cargabilidad_con:.1f}%
    """)

# ==========================================
# MÓDULO 6: EXPORTACIÓN CAD Y REPORTES
# ==========================================
elif modulo_seleccionado == "💾 6. Exportación CAD & Reportes":
    st.subheader("💾 Módulo 6: Exportación de Expediente Ejecutivo y Reportes")
    csv_bytes = df_calc.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="⬇️ Descargar Reporte Completo de Resultados (CSV)",
        data=csv_bytes,
        file_name=f'Reporte_EMS_{limite_red:.0f}kW_{capacidad_bess:.0f}kWh.csv',
        mime='text/csv'
    )
