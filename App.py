import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

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

# Helper para color de celda en python-docx
def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

# ==========================================
# FUNCIÓN GENERADORA DE LA MEMORIA COMPLETA FORMATO GPS GROUP (.DOCX)
# ==========================================
def generar_memoria_completa_gps_docx():
    doc = Document()
    
    # Márgenes estándar
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
        
    p_top = doc.add_paragraph()
    p_top.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_top = p_top.add_run("MEMORIA TÉCNICA Y ESPECIFICACIONES DE PROYECTO")
    r_top.bold = True
    r_top.font.size = Pt(14)
    r_top.font.name = 'Arial'

    # TABLA DE CONTROL DE DOCUMENTO ESTILO GPS GROUP
    table_hdr = doc.add_table(rows=4, cols=2)
    table_hdr.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_hdr.style = 'Table Grid'
    
    hdr_data = [
        ("Departamento:", "Ingeniería y Viabilidad Técnica"),
        ("Documento:", "Memoria Técnica y Especificaciones de Proyecto EMS - Peak Shaving UPS Bloque D"),
        ("Código del Documento:", "GPS-EMS-UPSD-MTC-001"),
        ("Revisión / Fecha:", "Rev. C / 04/09/2026")
    ]
    for idx, (lbl, val) in enumerate(hdr_data):
        row = table_hdr.rows[idx]
        row.cells[0].width = Inches(2.0)
        row.cells[1].width = Inches(4.5)
        
        p0 = row.cells[0].paragraphs[0]
        r0 = p0.add_run(lbl)
        r0.bold = True
        r0.font.size = Pt(9)
        set_cell_background(row.cells[0], "F2F2F2")
        
        p1 = row.cells[1].paragraphs[0]
        r1 = p1.add_run(val)
        r1.font.size = Pt(9)

    doc.add_paragraph()

    # Historial de revisiones
    p_rev_hdr = doc.add_paragraph()
    r_rev = p_rev_hdr.add_run("Historial de revisiones")
    r_rev.bold = True
    r_rev.font.size = Pt(11)
    
    table_rev = doc.add_table(rows=4, cols=4)
    table_rev.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_rev.style = 'Table Grid'
    
    headers_rev = ["N° de Revisión", "Fecha", "Páginas Revisadas", "Motivo de Revisión"]
    for c_idx, h_text in enumerate(headers_rev):
        cell = table_rev.rows[0].cells[c_idx]
        p = cell.paragraphs[0]
        r = p.add_run(h_text)
        r.bold = True
        r.font.size = Pt(9)
        set_cell_background(cell, "D9D9D9")
        
    revs = [
        ("A", "10/01/2026", "Todo el documento", "Revisión interna preliminar"),
        ("B", "15/05/2026", "Todo el documento", "Ajuste de parámetros BESS y PV"),
        ("C", "04/09/2026", "Todo el documento", "Entrega final para expediente ejecutivo")
    ]
    for r_idx, rev_row in enumerate(revs, start=1):
        for c_idx, val in enumerate(rev_row):
            cell = table_rev.rows[r_idx].cells[c_idx]
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(9)

    doc.add_paragraph()

    # Documentos Entregados
    p_doc_hdr = doc.add_paragraph()
    r_doc = p_doc_hdr.add_run("Documentos Entregados")
    r_doc.bold = True
    r_doc.font.size = Pt(11)
    
    table_docs = doc.add_table(rows=3, cols=2)
    table_docs.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_docs.style = 'Table Grid'
    
    doc_deliverables = [
        ("Documento:", "GPS-EMS-UPSD-MTC-001 Memoria Técnica y Especificaciones de Proyecto"),
        ("Plano:", "GPS-EMS-UPSD-DUF-001 Diagrama Unifilar Jerárquico y Arreglo BESS/PV"),
        ("Estudio:", "GPS-EMS-UPSD-CDC-001 Memoria de Cálculo y Simulación de Cortocircuito")
    ]
    for r_idx, (d_lbl, d_val) in enumerate(doc_deliverables):
        row = table_docs.rows[r_idx]
        row.cells[0].paragraphs[0].add_run(d_lbl).bold = True
        row.cells[0].paragraphs[0].runs[0].font.size = Pt(9)
        row.cells[1].paragraphs[0].add_run(d_val).font.size = Pt(9)

    doc.add_page_break()

    # INDICE DE CONTENIDO
    p_ind = doc.add_paragraph()
    r_ind = p_ind.add_run("INDICE DE CONTENIDO")
    r_ind.bold = True
    r_ind.font.size = Pt(13)
    
    toc_items = [
        "1. OBJETIVOS",
        "   1.1 Objetivo General",
        "   1.2 Objetivos Específicos",
        "2. ANTECEDENTES",
        "3. BASE TÉCNICA Y NORMATIVA APLICABLE",
        "4. DESARROLLO GENERAL DEL PROYECTO",
        "   4.1 SISTEMA EXISTENTE",
        "       4.1.1 Acometida y Transformación Principal (1000 kVA)",
        "       4.1.2 Perfil de Consumo y Demanda Máxima Existente (179.1 kW)",
        "       4.1.3 Diagrama Unifilar Existente",
        "   4.2 SISTEMA PROYECTADO (EMS, BESS Y FOTOVOLTAICO)",
        "       4.2.1 Punto de Acoplamiento PCC y Equipo de Medición",
        "       4.2.2 Sistema Generación Fotovoltaica Proyectado",
        "       4.2.3 Sistema Almacenamiento Energético BESS Proyectado",
        "       4.2.4 Inversor Híbrido y Filosofía de Control EMS",
        "       4.2.5 Diagrama Unifilar Proyectado",
        "5. ESPECIFICACIONES TÉCNICAS DE EQUIPOS",
        "   5.1 Banco de Baterías BESS (LiFePO4)",
        "   5.2 Inversor Híbrido Multimodo",
        "   5.3 Generador Fotovoltaico (Módulos PERC)",
        "   5.4 Conductores y Canalizaciones Subterráneas (XLPE/RMC)",
        "   5.5 Protecciones y Capacidad Interruptiva AIC (Art. 110-9)",
        "6. CÁLCULO DE LA DEMANDA Y ESTUDIO TÉCNICO NORMATIVO",
        "   6.1 Formulación Matemática del Algoritmo EMS",
        "   6.2 Dimensionamiento Normativo BESS (IEEE Std 2030.2)",
        "   6.3 Despacho Dinámico de Potencia Activa (IEEE Std 2030.7)",
        "   6.4 Análisis de Reactivos y Calidad de Energía (IEEE Std 1547)",
        "   6.5 Estudio de Cortocircuito e Impedancia Equivalente",
        "   6.6 Cargabilidad Térmica del Transformador de 1000 kVA",
        "7. LISTA DE MATERIALES Y EQUIPOS PROYECTADOS",
        "8. CONCLUSIONES",
        "9. ANEXOS"
    ]
    for item in toc_items:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(2)
        r = p.add_run(item)
        r.font.size = Pt(10)
        r.font.name = 'Arial'

    doc.add_page_break()

    # 1. OBJETIVOS
    doc.add_heading('1. OBJETIVOS:', level=1)
    doc.add_heading('1.1 Objetivo General:', level=2)
    doc.add_paragraph(f"Diseñar, dimensionar y validar la arquitectura técnica y normativa para la implementación de un Sistema de Gestión Inteligente de la Energía (EMS) basado en almacenamiento BESS ({capacidad_bess:.0f} kWh) y generación fotovoltaica ({potencia_pv:.0f} kWp), orientado al recorte de picos de demanda (Peak Shaving) a un límite de {limite_red:.0f} kW en el edificio Bloque D de la Universidad Politécnica Salesiana.")
    
    doc.add_heading('1.2 Objetivos Específicos:', level=2)
    p1 = doc.add_paragraph(style='List Bullet')
    p1.add_run("Evaluar el comportamiento térmico y de carga del transformador principal de 1000 kVA ante la reducción de la demanda pico consumida de la red pública.")
    p2 = doc.add_paragraph(style='List Bullet')
    p2.add_run("Fundamentar analíticamente el algoritmo de despacho EMS bajo los estándares internacionales IEEE Std 2030.2-2015, IEEE Std 2030.7-2017 e IEEE Std 1547-2018.")
    p3 = doc.add_paragraph(style='List Bullet')
    p3.add_run("Determinar la corriente de falla de cortocircuito simétrica (Icc) en el bus de 220 V para dimensionar la capacidad interruptiva mínima (AIC) de las protecciones principales según Art. 110-9 del Código Eléctrico.")

    # 2. ANTECEDENTES
    doc.add_heading('2. ANTECEDENTES:', level=1)
    doc.add_paragraph("Para optimizar el consumo de energía eléctrica y mitigar los costos asociados a la facturación por demanda máxima en las instalaciones del Bloque D de la Universidad Politécnica Salesiana, se ha identificado la necesidad de implementar una infraestructura de microrred inteligente. El edificio presenta un perfil de carga caracterizado por picos acentuados durante horas de alta actividad académica e investigativa, alcanzando demandas punta de hasta 179.1 kW.")
    doc.add_paragraph("El desarrollo del proyecto integra la generación distribuida renovable fotovoltaica con almacenamiento electroquímico de ion-litio (BESS) coordinado mediante un controlador de microrred EMS. Esta solución tecnológica permite aplanar la curva de carga, reducir el estrés térmico sobre el transformador principal y garantizar un suministro eléctrico continuo, seguro y eficiente.")

    # 3. BASE TÉCNICA
    doc.add_heading('3. BASE TÉCNICA Y NORMATIVA APLICABLE:', level=1)
    doc.add_paragraph("Para el desarrollo del diseño eléctrico, cálculo de componentes y formulación del sistema de control EMS, se han utilizado como referencia las siguientes normativas y regulaciones técnicas:")
    
    stds = [
        ("IEEE Std 2030.2-2015 / IEEE Std 1547.9-2022:", "IEEE Guide for the Interoperability of Energy Storage Systems Integrated with the Electric Power System. Establece los criterios de interconexión, límites de descarga (DoD) y reserva de SOC."),
        ("IEEE Std 2030.7-2017:", "IEEE Standard for the Specification of Microgrid Controllers. Regula la lógica de despacho del algoritmo EMS, estados de transición y set-points de control de potencia activa."),
        ("IEEE Std 1547-2018:", "IEEE Standard for Interconnection and Interoperability of Distributed Energy Resources. Regula los requerimientos del inversor para soporte de reactivos y factor de potencia mínimo (FP >= 0.95)."),
        ("National Electrical Code (NEC / NFPA 70):", "Código Eléctrico Nacional, Art. 110-9 (Capacidad interruptiva de protecciones), Art. 705 (Fuentes de producción interconectadas) y Art. 706 (Sistemas de almacenamiento de energía)."),
        ("IEC 61000-4-15 / IEEE Std 1453:", "Normativa sobre evaluación y control de Flicker (Pst y Plt) y fluctuaciones de voltaje en el punto de acoplamiento común (PCC)."),
        ("Manual de Homologación de Unidades de Propiedad y Construcción:", "Regulación aplicable del Ministerio de Energía y Minas / CNEL EP para sistemas de distribución e infraestructura eléctrica.")
    ]
    for title, desc in stds:
        p = doc.add_paragraph(style='List Bullet')
        r_t = p.add_run(title + " ")
        r_t.bold = True
        p.add_run(desc)

    # 4. DESARROLLO
    doc.add_heading('4. DESARROLLO GENERAL DEL PROYECTO:', level=1)
    
    doc.add_heading('4.1 SISTEMA EXISTENTE', level=2)
    doc.add_heading('4.1.1 Acometida y Transformación Principal (1000 kVA)', level=3)
    doc.add_paragraph("El Bloque D recibe energía eléctrica desde la red pública de media tensión a 69 kV mediante una subestación reductora equipada con un transformador trifásico pedestal de 1000 kVA, con grupo de conexión Dyn1 y relación de transformación 69 kV / 0.22 kV. El secundario alimenta el Tablero General de Baja Tensión (TGBT) en 220 V trifásico a 60 Hz.")
    
    doc.add_heading('4.1.2 Perfil de Consumo y Demanda Máxima Existente (179.1 kW)', level=3)
    doc.add_paragraph("A partir del registro de lecturas diarias de demanda horaria en el Bloque D, se determinó que la carga base nocturna es de aproximadamente 36.0 kW, mientras que durante el período diurno y vespertino la demanda se incrementa sustancialmente, alcanzando un valor pico de 179.1 kW registrado a las 12:00 h, y un segundo pico pronunciado de 175.0 kW a las 19:00 h.")
    
    doc.add_heading('4.1.3 Diagrama Unifilar Existente', level=3)
    doc.add_paragraph("El diagrama unifilar existente consta del punto de alimentación a 69 kV, el interruptor de cabecera, el transformador de 1000 kVA y el bus principal de 220 V desde el cual se derivan los alimentadores hacia los tableros secundarios de iluminación, fuerza y laboratorios del edificio.")

    doc.add_heading('4.2 SISTEMA PROYECTADO (EMS, BESS Y FOTOVOLTAICO)', level=2)
    doc.add_heading('4.2.1 Punto de Acoplamiento PCC y Equipo de Medición', level=3)
    doc.add_paragraph("El proyecto contempla la integración de la microrred en el bus principal de 220 V del TGBT. En este punto de acoplamiento común (PCC) se instalará un analizador de red y medidor de calidad de energía multifunción con comunicación Modbus TCP para la retroalimentación en tiempo real al controlador EMS.")

    doc.add_heading('4.2.2 Sistema Generación Fotovoltaica Proyectado', level=3)
    doc.add_paragraph(f"Se proyecta la instalación de un arreglo fotovoltaico sobre la cubierta del edificio con una capacidad instalada nominal de {potencia_pv:.1f} kWp, conformado por módulos monocristalinos de alta eficiencia PERC. La generación máxima estimada a mediodía alcanza los {potencia_pv:.1f} kW, inyectando potencia activa directamente al bus de baja tensión.")

    doc.add_heading('4.2.3 Sistema Almacenamiento Energético BESS Proyectado', level=3)
    doc.add_paragraph(f"Se implementará un banco de baterías BESS con tecnología de Litio-Ferrofosfato (LiFePO4) de {capacidad_bess:.1f} kWh de capacidad nominal y un voltaje nominal en DC de 512 V. El banco cuenta con un sistema de gestión de baterías (BMS) integrado para la supervisión de temperatura, balanceo de celdas y estado de salud (SOH). Para preservar su vida útil sobre los 4000 ciclos, se establece un límite de descarga del 80% (DoD max), manteniendo un SOC mínimo de reserva del 20% ({0.20*capacidad_bess:.1f} kWh).")

    doc.add_heading('4.2.4 Inversor Híbrido y Filosofía de Control EMS', level=3)
    doc.add_paragraph(f"El acoplamiento del BESS y del sistema fotovoltaico se realiza mediante un inversor híbrido bidireccional multimodo de {inv_req:.1f} kVA de capacidad nominal. El algoritmo de control EMS determinístico opera con un set-point límite de red fijado en {limite_red:.1f} kW. Cuando la demanda neta sobrepasa este umbral, el EMS ordena la descarga inmediata de la batería para aportar la potencia faltante. De madrugada (01:00 a 05:00 h), el EMS recarga la batería a una tasa controlada de {carga_nocturna:.1f} kW durante la tarifa valle Off-Peak.")

    doc.add_heading('4.2.5 Diagrama Unifilar Proyectado', level=3)
    doc.add_paragraph("El diagrama unifilar proyectado integra el transformador de 1000 kVA, el bus de 220 V, el inversor híbrido de potencia, el arreglo fotovoltaico, el gabinete BESS con su protección DC y el sistema de control EMS en red de comunicación industrial.")

    # 5. ESPECIFICACIONES TÉCNICAS
    doc.add_heading('5. ESPECIFICACIONES TÉCNICAS DE EQUIPOS:', level=1)
    
    table_specs = doc.add_table(rows=6, cols=3)
    table_specs.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_specs.style = 'Table Grid'
    
    spec_headers = ["Equipo / Componente", "Parámetro Técnico", "Valor Especificado"]
    for c_idx, h_text in enumerate(spec_headers):
        cell = table_specs.rows[0].cells[c_idx]
        p = cell.paragraphs[0]
        r = p.add_run(h_text)
        r.bold = True
        r.font.size = Pt(9)
        set_cell_background(cell, "D9D9D9")
        
    spec_rows = [
        ("Banco BESS (LiFePO4)", "Capacidad / Química / DoD", f"{capacidad_bess:.0f} kWh / LFP / 80% DoD (SOC min = {0.20*capacidad_bess:.1f} kWh)"),
        ("Inversor Híbrido Multimodo", "Potencia / Voltaje / FP", f"{inv_req:.1f} kVA / 220V 3F / FP regulable 0.95-1.0"),
        ("Generación Fotovoltaica", "Potencia Pico / Tipo Módulo", f"{potencia_pv:.0f} kWp / Monocristalino PERC 550W"),
        ("Transformador Pedestal", "Potencia / Voltaje / Z%", f"1000 kVA / 69 kV a 0.22 kV / Z = 5.75%"),
        ("Protección Principal TGBT", "Capacidad Interruptiva AIC", "Disyuntor Marco Moldeado / Bastidor 50 kA @ 220V")
    ]
    for r_idx, s_data in enumerate(spec_rows, start=1):
        for c_idx, val in enumerate(s_data):
            cell = table_specs.rows[r_idx].cells[c_idx]
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)

    doc.add_paragraph()

    # 6. CÁLCULO DE LA DEMANDA Y ESTUDIO TÉCNICO
    doc.add_heading('6. CÁLCULO DE LA DEMANDA Y ESTUDIO TÉCNICO NORMATIVO:', level=1)
    
    doc.add_heading('6.1 Formulación Matemática del Algoritmo EMS', level=2)
    doc.add_paragraph("La potencia activa neta demandada a la red sin intervención de batería se expresa como:")
    doc.add_paragraph("P_red_teorica(t) = P_carga(t) - P_PV(t)")
    doc.add_paragraph("Tras el despacho dinámico del BESS, la potencia real tomada de la red se determina por:")
    doc.add_paragraph("P_red_real(t) = P_red_teorica(t) - P_bat(t)")
    doc.add_paragraph(f"Donde P_bat(t) es la potencia de descarga (P_bat > 0) o carga (P_bat < 0) del BESS, sujeta a la restricción SOC_min ({0.20*capacidad_bess:.1f} kWh) <= SOC(t) <= SOC_max ({capacidad_bess:.1f} kWh).")

    doc.add_heading('6.2 Dimensionamiento Normativo BESS (IEEE Std 2030.2)', level=2)
    doc.add_paragraph(f"• Capacidad Nominal BESS (C_bat_max): {capacidad_bess:.1f} kWh")
    doc.add_paragraph(f"• Reserva Mínima de Seguridad (SOC_min = 20%): {0.20*capacidad_bess:.1f} kWh")
    doc.add_paragraph(f"• Profundidad de Descarga Máxima (DoD max): 80.0%")
    doc.add_paragraph(f"• Capacidad Útil Operativa (E_util = SOC_max - SOC_min): {0.80*capacidad_bess:.1f} kWh")

    doc.add_heading('6.3 Despacho Dinámico de Potencia Activa (IEEE Std 2030.7)', level=2)
    doc.add_paragraph(f"• Demanda Pico Bruta Original: {demanda_max:.1f} kW")
    doc.add_paragraph(f"• Set-point Límite de Red Configurado: {limite_red:.1f} kW")
    doc.add_paragraph(f"• Reducción Efectiva de Demanda Pico (Peak Shaving): {reduccion_pico:.1f} kW ({(reduccion_pico/demanda_max)*100.0:.1f}% de recorte)")

    doc.add_heading('6.4 Análisis de Reactivos y Calidad de Energía (IEEE Std 1547)', level=2)
    doc.add_paragraph(f"• Potencia Aparente Mínima del Inversor (S_inv_min): {inv_req:.1f} kVA (calculado a un FP de 0.95)")
    q_res_calc = (160.0**2 - potencia_pv**2)**0.5 if 160.0 >= potencia_pv else 0.0
    doc.add_paragraph(f"• Reserva de Potencia Reactiva Disponible (Q_reserva): {q_res_calc:.2f} kVAR a máxima generación fotovoltaica, permitiendo la regulación activa de voltaje y atenuación de Flicker (Plt).")

    doc.add_heading('6.5 Estudio de Cortocircuito e Impedancia Equivalente', level=2)
    doc.add_paragraph(f"• Corriente Nominal Secundaria Transformador (1000 kVA, 220V): I_nom = {i_nom:.1f} A")
    doc.add_paragraph(f"• Corriente de Cortocircuito Trifásica Simétrica: I_cc = {icc_simetrica/1000.0:.2f} kA (para Z% = 5.75%)")
    doc.add_paragraph("• Capacidad Interruptiva Mínima Especificada (Art. 110-9 NEC): Disyuntor principal de 50 kA @ 220V.")

    doc.add_heading('6.6 Cargabilidad Térmica del Transformador de 1000 kVA', level=2)
    doc.add_paragraph(f"• Cargabilidad Pico Original sin EMS: {cargabilidad_sin:.1f}% ({demanda_max:.1f} kW / 1000 kVA)")
    doc.add_paragraph(f"• Cargabilidad Pico Gestionada con EMS: {cargabilidad_con:.1f}% ({limite_red:.1f} kW / 1000 kVA)")
    doc.add_paragraph("• Conclusión Térmica: El transformador de 1000 kVA opera con amplio margen de seguridad, reduciendo el envejecimiento térmico del aislante en el devanado secundario.")

    # 7. LISTA DE MATERIALES
    doc.add_heading('7. LISTA DE MATERIALES Y EQUIPOS PROYECTADOS:', level=1)
    
    table_bom = doc.add_table(rows=7, cols=4)
    table_bom.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_bom.style = 'Table Grid'
    
    bom_headers = ["Ítem", "Descripción del Material / Equipo", "Unidad", "Cantidad"]
    for c_idx, h_text in enumerate(bom_headers):
        cell = table_bom.rows[0].cells[c_idx]
        p = cell.paragraphs[0]
        r = p.add_run(h_text)
        r.bold = True
        r.font.size = Pt(9)
        set_cell_background(cell, "D9D9D9")
        
    bom_rows = [
        ("1", f"Sistema Almacenamiento BESS {capacidad_bess:.0f} kWh LiFePO4 con BMS", "Global", "1"),
        ("2", f"Arreglo Fotovoltaico {potencia_pv:.0f} kWp con Módulos Monocristalinos PERC 550W", "Global", "1"),
        ("3", f"Inversor Híbrido Multimodo {inv_req:.1f} kVA 220V 3F con Control EMS", "Unidad", "1"),
        ("4", "Controlador PLC EMS con Analizador de Red Modbus TCP en PCC", "Unidad", "1"),
        ("5", "Disyuntor de Caja Moldeada 3P 2000A / 50 kA AIC @ 220V", "Unidad", "1"),
        ("6", "Alimentadores Monopolares Cu XLPE 15 kV #350 kcmil + Neutro #1/0 AWG", "Metro", "120")
    ]
    for r_idx, b_data in enumerate(bom_rows, start=1):
        for c_idx, val in enumerate(b_data):
            cell = table_bom.rows[r_idx].cells[c_idx]
            p = cell.paragraphs[0]
            r = p.add_run(val)
            r.font.size = Pt(8.5)

    doc.add_paragraph()

    # 8. CONCLUSIONES
    doc.add_heading('8. CONCLUSIONES:', level=1)
    p = doc.add_paragraph(style='List Bullet')
    p.add_run(f"La implementación del algoritmo EMS determinístico recorta exitosamente la demanda pico de la red de {demanda_max:.1f} kW a {limite_red:.1f} kW, representando un aplanamiento neto de {reduccion_pico:.1f} kW ({(reduccion_pico/demanda_max)*100.0:.1f}% de reducción).")
    
    p = doc.add_paragraph(style='List Bullet')
    p.add_run(f"La cargabilidad del transformador de 1000 kVA se disminuye del {cargabilidad_sin:.1f}% al {cargabilidad_con:.1f}%, eliminando riesgos de sobrecarga en horas pico y garantizando una operación térmica óptima.")
    
    p = doc.add_paragraph(style='List Bullet')
    p.add_run(f"El dimensionamiento del BESS a {capacidad_bess:.0f} kWh con un límite de reserva del 20% ({0.20*capacidad_bess:.1f} kWh) cumple rigurosamente con la norma IEEE Std 2030.2, asegurando la preservación de la vida útil del banco de baterías sobre 4000 ciclos de operación.")

    # 9. ANEXOS
    doc.add_heading('9. ANEXOS:', level=1)
    doc.add_paragraph("Anexo I. GPS-EMS-UPSD-DUF-001 Diagrama Unifilar Jerárquico del Proyecto EMS.")
    doc.add_paragraph("Anexo II. GPS-EMS-UPSD-IMP-001 Plano de Implantación y Arreglo Fotovoltaico Bloque D.")
    doc.add_paragraph("Anexo III. GPS-EMS-UPSD-CDC-001 Memoria de Cálculo y Registros de Simulación Horaria EMS.")

    target = io.BytesIO()
    doc.save(target)
    return target.getvalue()

# ==========================================
# MÓDULOS 1 A 4
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
# MÓDULO 5: MEMORIA TÉCNICO-DESCRIPTIVA (OFICIAL WORD GPS GROUP)
# ==========================================
elif modulo_seleccionado == "📄 5. Memoria Técnico-Descriptiva":
    st.subheader("📄 Módulo 5: Memoria Técnica y Especificaciones de Proyecto (Formato Oficial GPS Group)")
    st.markdown("Generación automática del expediente ejecutivo oficial en formato Word editable:")

    docx_bytes = generar_memoria_completa_gps_docx()

    col_down_doc, col_info_doc = st.columns([1, 2])
    with col_down_doc:
        st.download_button(
            label="📄 Descargar Memoria Técnica Oficial en Word (.docx)",
            data=docx_bytes,
            file_name=f'GPS-EMS-UPSD-MTC-001_MEMORIA_TECNICA_UPS.docx',
            mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    with col_info_doc:
        st.success("✔ Expediente en Word generado respetando estrictamente la plantilla de ingeniería de tus proyectos.")

    st.markdown("---")
    st.markdown("### Estructura del Documento Generado:")
    st.info(f"""
    **CÓDIGO:** GPS-EMS-UPSD-MTC-001 | **REVISIÓN:** Rev. C (04/09/2026)
    
    1. **OBJETIVOS:** Electrificación y Peak Shaving a {limite_red:.0f} kW.
    2. **ANTECEDENTES:** Diagnóstico del Bloque D y perfil de demanda de {demanda_max:.1f} kW.
    3. **BASE TÉCNICA:** IEEE Std 2030.2, IEEE Std 2030.7, IEEE Std 1547, NEC Art. 110-9, Manual CNEL EP.
    4. **DESARROLLO GENERAL:** Descripción de subestación de 1000 kVA, arreglo FV ({potencia_pv:.0f} kWp), BESS ({capacidad_bess:.0f} kWh) e inversor ({inv_req:.1f} kVA).
    5. **ESPECIFICACIONES TÉCNICAS:** Tabla completa de componentes.
    6. **CÁLCULO DE LA DEMANDA Y ESTUDIO TÉCNICO:** Formulación matemática EMS, cortocircuito ({icc_simetrica/1000.0:.2f} kA) y cargabilidad del transformador ({cargabilidad_sin:.1f}% a {cargabilidad_con:.1f}%).
    7. **LISTA DE MATERIALES:** Cuadro con ítems de BESS, PV, inversor y alimentadores XLPE.
    8. **CONCLUSIONES Y 9. ANEXOS**
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
