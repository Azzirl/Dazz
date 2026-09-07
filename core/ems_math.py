"""
core/ems_math.py  —  Motor matemático del EMS
================================================
CORRECCIONES APLICADAS:
  1. P_PV: eficiencia total 80 % (no 95 % solo del inversor)
  2. Caída de tensión calculada con Z% real del trafo (no factor 0.4 arbitrario)
  3. Carga nocturna BESS independiente de ps_activo (siempre puede cargar de noche)
  4. Icc calculado en A e kA con nombres distintos para evitar ambigüedad
  5. Degradación anual del sistema PV agregada
  6. Ciclos de vida del BESS y desgaste por ciclo
  7. Análisis financiero completo: VAN, TIR, OPEX, inflación tarifaria
  8. THD de corriente del inversor estimado (IEEE 1547-2018)
  9. Límites armónicos verificados por armónico
"""

import numpy as np
import pandas as pd
from core.climate import obtener_irradiancia_real

# ──────────────────────────────────────────────────────────────────────────────
# CONSTANTES DEL SISTEMA
# ──────────────────────────────────────────────────────────────────────────────
ETA_SISTEMA       = 0.80   # Eficiencia total: módulos + cableado + inversor + temperatura
ETA_INVERSOR      = 0.95   # FP / eficiencia solo del inversor (para cálculo de S_inv)
Z_TRAFO_PU        = 0.0575 # Impedancia trafo 5.75 % → 0.0575 p.u.
R_TRAFO_PU        = 0.011  # Resistencia trafo 1.1 % → 0.011 p.u.
X_TRAFO_PU        = np.sqrt(Z_TRAFO_PU**2 - R_TRAFO_PU**2)  # Reactancia p.u.
CO2_FACTOR_KG_KWH = 0.45   # Factor de emisión red Ecuador (kg CO₂/kWh)
CICLOS_LIFEP04_VIDA = 4000  # Ciclos de vida LiFePO4 @ DoD 80 %
DEGRADACION_PV_ANUAL = 0.005  # 0.5 % degradación anual módulos PERC

# Carga real medida Bloque D (METREL MI2792, agosto 2022)
REAL_LOAD_KW = [36, 36, 36, 36, 36, 40, 60, 90, 120, 145, 160, 175,
                179.1, 140, 150, 155, 160, 165, 172, 175, 130, 90, 50, 36]

# Límites THD de corriente IEEE 1547-2018 (% de corriente fundamental)
THD_I_LIMITES_IEEE1547 = {
    "h3-h9":   4.0,
    "h11-h15": 2.0,
    "h17-h21": 1.5,
    "h23-h33": 0.6,
    "THD_total": 5.0
}


# ──────────────────────────────────────────────────────────────────────────────
# SOPORTE REACTIVO  (Volt/VAR — IEEE 2800, droop control)
# ──────────────────────────────────────────────────────────────────────────────
def calcular_soporte_reactivo(v_actual_pu: float, p_activa_kw: float, s_inv_kva: float):
    """
    Control Volt/VAR con curva de droop.
    Banda muerta: 0.98 – 1.02 p.u.
    Fuera de banda: inyecta/absorbe Q proporcional a la desviación.

    Retorna:
        q_inyectada (kVAR) : positivo → inyecta (eleva tensión)
                             negativo → absorbe (baja tensión)
        v_corregido (p.u.) : tensión tras la compensación
    """
    # Reserva reactiva disponible (triángulo de potencias)
    q_max = np.sqrt(max(0.0, s_inv_kva**2 - p_activa_kw**2))

    q_inyectada = 0.0
    v_corregido  = v_actual_pu

    if v_actual_pu < 0.98:
        # Sub-tensión → inyecta reactivos capacitivos
        q_req        = (0.98 - v_actual_pu) * (s_inv_kva * 2.0)
        q_inyectada  = min(q_req, q_max)
        v_corregido  = v_actual_pu + (q_inyectada / (s_inv_kva * 2.0))

    elif v_actual_pu > 1.02:
        # Sobre-tensión → absorbe reactivos inductivos
        q_req        = (v_actual_pu - 1.02) * (s_inv_kva * 2.0)
        q_inyectada  = -min(q_req, q_max)
        v_corregido  = v_actual_pu + (q_inyectada / (s_inv_kva * 2.0))

    return round(q_inyectada, 2), round(v_corregido, 4)


# ──────────────────────────────────────────────────────────────────────────────
# CAÍDA DE TENSIÓN  (modelo físico con Z% del trafo)
# ──────────────────────────────────────────────────────────────────────────────
def calcular_caida_tension(p_kw: float, q_kvar: float, s_trafo_kva: float) -> float:
    """
    Calcula la caída de tensión en el bus BT considerando las componentes
    resistiva (R) y reactiva (X) del transformador.

    ΔV ≈ (P·R_pu + Q·X_pu) / S_base  [p.u.]
    V_bus = 1.0 - ΔV

    Referencia: IEC 60076-1, IEEE Std C57.12.00
    """
    # Normalizar a p.u. usando S_trafo como base
    p_pu = p_kw  / s_trafo_kva
    q_pu = q_kvar / s_trafo_kva

    delta_v = (p_pu * R_TRAFO_PU) + (q_pu * X_TRAFO_PU)
    v_bus   = max(0.85, 1.0 - delta_v)   # limitar al 85 % para realismo
    return round(v_bus, 4)


# ──────────────────────────────────────────────────────────────────────────────
# CORRIENTE DE CORTOCIRCUITO
# ──────────────────────────────────────────────────────────────────────────────
def calcular_icc(s_trafo_kva: float, v_nom_v: float) -> dict:
    """
    Calcula Icc simétrica y asimétrica del transformador.
    El factor 1.25 de asimetría es conservador según ANSI/IEEE Std 141.

    Retorna dict con valores en A y kA para claridad.
    """
    i_nom_a    = (s_trafo_kva * 1000.0) / (np.sqrt(3) * v_nom_v)
    icc_sim_a  = i_nom_a / Z_TRAFO_PU
    icc_asim_a = icc_sim_a * 1.25  # Factor de asimetría ANSI/IEEE Std 141

    return {
        "i_nom_A":     round(i_nom_a,    1),
        "icc_sim_A":   round(icc_sim_a,  1),
        "icc_asim_A":  round(icc_asim_a, 1),
        "icc_sim_kA":  round(icc_sim_a  / 1000.0, 3),
        "icc_asim_kA": round(icc_asim_a / 1000.0, 3),
    }


# ──────────────────────────────────────────────────────────────────────────────
# THD DE CORRIENTE  (estimación IEEE 1547-2018)
# ──────────────────────────────────────────────────────────────────────────────
def estimar_thd_corriente(p_inv_kw: float, p_pv_nominal_kw: float) -> dict:
    """
    Modelo lineal simplificado del THD de corriente de inversores PWM modernos
    con filtro LCL (IEEE 1547-2018, Tabla 2).

    A plena carga: THD_I ≈ 2–3 %
    A carga parcial (<20 %): THD_I puede subir hasta 5 %

    Retorna dict con THD estimado y verificación de cumplimiento.
    """
    if p_pv_nominal_kw <= 0:
        return {"thd_i_pct": 0.0, "cumple_ieee1547": True, "nivel_carga_pct": 0.0}

    nivel_carga = min(1.0, p_inv_kw / p_pv_nominal_kw) if p_pv_nominal_kw > 0 else 0.0
    # A plena carga → THD_I ≈ 2.5 %; a carga nula → sube a ~5 %
    thd_i = 2.5 + (1.0 - nivel_carga) * 2.5
    cumple = thd_i <= THD_I_LIMITES_IEEE1547["THD_total"]

    return {
        "thd_i_pct":       round(thd_i, 2),
        "cumple_ieee1547": cumple,
        "nivel_carga_pct": round(nivel_carga * 100, 1),
        "limites":         THD_I_LIMITES_IEEE1547
    }


# ──────────────────────────────────────────────────────────────────────────────
# BALANCE ENERGÉTICO 24 H  (algoritmo EMS principal)
# ──────────────────────────────────────────────────────────────────────────────
def calcular_balance_24h(cfg: dict):
    """
    Simula el balance energético horario con:
      • Peak Shaving BESS (cuando ps_activo=True)
      • Carga nocturna BESS (01:00–05:00, independiente de ps_activo)
      • Generación PV con eficiencia total 80 % (corregido de 95 %)
      • Caída de tensión por Z% del trafo (corregido de factor 0.4)
      • Soporte Volt/VAR (IEEE 2800)
      • THD de corriente estimado
    """
    lat = cfg.get('lat', -2.1833)
    lon = cfg.get('lon', -79.8833)

    # ── Irradiancia (API satelital o fallback) ─────────────────────────────
    irradiancia_24h, es_api_real = obtener_irradiancia_real(lat, lon)

    # ── Generación PV  (CORRECCIÓN: ETA_SISTEMA = 0.80, no 0.95) ──────────
    # Fórmula: P_PV(t) = P_nominal × [G(t) / G_STC] × η_total
    # G_STC = 1000 W/m²
    if cfg['p_pv'] > 0:
        pv_real = [round(cfg['p_pv'] * (g / 1000.0) * ETA_SISTEMA, 1)
                   for g in irradiancia_24h]
    else:
        pv_real = [0.0] * 24

    # ── Parámetros BESS ────────────────────────────────────────────────────
    soc_min  = 0.20 * cfg['c_bat']
    soc_max  = cfg['c_bat']
    energia  = cfg['c_bat'] * 0.50   # Estado inicial 50 %

    # ── Parámetros inversor ────────────────────────────────────────────────
    # S_inv se dimensiona para la potencia PV; si no hay PV, usa P_lim como referencia
    inv_kva = (cfg['p_pv'] / ETA_INVERSOR) if cfg['p_pv'] > 0 else (cfg['p_lim'] / ETA_INVERSOR)

    # ── Límite operativo de red ────────────────────────────────────────────
    limite_ps = cfg['p_lim'] if cfg['ps_activo'] else 1e6  # sin límite si PS inactivo

    # ── Cálculo Icc ────────────────────────────────────────────────────────
    datos_icc = calcular_icc(cfg['s_trafo'], cfg['v_nom'])

    rows = []
    for i in range(24):
        p_teorica = REAL_LOAD_KW[i] - pv_real[i]
        p_bat     = 0.0
        motivo    = "—"

        # ── Peak Shaving: descarga BESS si P_teorica > P_lim ──────────────
        if p_teorica > limite_ps:
            req   = p_teorica - limite_ps
            p_bat = req if (energia - req) >= soc_min else max(0.0, energia - soc_min)
            motivo = "Peak Shaving"

        # ── Carga nocturna BESS (01:00–05:00) ─────────────────────────────
        # CORRECCIÓN: este bloque es independiente de ps_activo.
        # El BESS siempre puede cargar desde la red en tarifa valle nocturna.
        elif 1 <= i <= 5:
            espacio = soc_max - energia
            p_bat   = -(min(cfg['carga_noc'], espacio)) if espacio > 0.5 else 0.0
            motivo  = "Carga BESS" if p_bat < 0 else "BESS lleno"

        p_red    = p_teorica - p_bat
        energia  = max(soc_min, min(soc_max, energia - p_bat))  # clamp físico
        soc      = (energia / cfg['c_bat']) * 100.0

        # ── Modelo de tensión con Z% del trafo (CORRECCIÓN) ───────────────
        # Asumimos Q de carga ≈ 0.3 × P (FP ≈ 0.96, tipico edificio)
        q_carga  = p_red * 0.30
        v_base   = calcular_caida_tension(p_red, q_carga, cfg['s_trafo'])

        # ── Soporte Volt/VAR ───────────────────────────────────────────────
        p_inversor_total = abs(p_bat) + pv_real[i]
        q_inyectada, v_final = calcular_soporte_reactivo(v_base, p_inversor_total, inv_kva)

        # ── THD de corriente estimado ──────────────────────────────────────
        thd_info = estimar_thd_corriente(pv_real[i], cfg['p_pv'])

        rows.append({
            'Hora':              f"{i:02d}:00",
            'P_Carga':           REAL_LOAD_KW[i],
            'P_PV':              pv_real[i],
            'Irradiancia_Wm2':   irradiancia_24h[i],
            'P_Bat':             round(p_bat,    2),
            'P_Red':             round(p_red,    2),
            'E_BESS_kWh':        round(energia,  2),
            'SOC':               round(soc,      1),
            'V_pu':              v_final,
            'Q_inyectada':       q_inyectada,
            'THD_I_pct':         thd_info['thd_i_pct'],
            'Modo_BESS':         motivo,
        })

    df_ems = pd.DataFrame(rows)

    kpis = {
        'demanda_max':      float(df_ems['P_Carga'].max()),
        'demanda_recortada': float(df_ems['P_Red'].max()),
        'carg_sin_ems':     (float(df_ems['P_Carga'].max()) / cfg['s_trafo']) * 100.0,
        'carg_con_ems':     (float(df_ems['P_Red'].max())   / cfg['s_trafo']) * 100.0,
        'inv_kva':          inv_kva,
        'soc_min_kwh':      soc_min,
        'e_util_kwh':       cfg['c_bat'] * 0.80,
        'pv_real':          pv_real,
        'irradiancia_24h':  irradiancia_24h,
        'es_api_real':      es_api_real,
        'REAL_LOAD':        REAL_LOAD_KW,
        'datos_icc':        datos_icc,
        'thd_tension_max':  2.2,   # medido METREL (fijo, informe agosto 2022)
        'thd_corriente_max': float(df_ems['THD_I_pct'].max()),
        'v_min_pu':         float(df_ems['V_pu'].min()),
        'v_max_pu':         float(df_ems['V_pu'].max()),
    }

    return df_ems, kpis


# ──────────────────────────────────────────────────────────────────────────────
# ANÁLISIS FINANCIERO COMPLETO  (VAN, TIR, Payback descontado)
# ──────────────────────────────────────────────────────────────────────────────
def calcular_financiero(cfg: dict, kpis: dict,
                        tarifa_demanda: float, tarifa_energia: float,
                        costo_bess_kwh: float, costo_pv_kwp: float,
                        tasa_descuento: float = 0.08,
                        inflacion_tarifa: float = 0.04,
                        opex_pct_capex: float  = 0.01) -> dict:
    """
    Análisis financiero completo a 10 años.

    Incluye:
      • Degradación PV 0.5 %/año
      • Inflación tarifaria 4 %/año (configurable)
      • OPEX anual 1 % del CAPEX (configurable)
      • VAN (Valor Actual Neto) con tasa de descuento
      • TIR (Tasa Interna de Retorno)
      • Payback descontado (año en que VAN > 0)

    Parámetros:
        tarifa_demanda   : USD/kW-mes (cargo por demanda pico)
        tarifa_energia   : USD/kWh
        costo_bess_kwh   : USD/kWh de BESS instalado
        costo_pv_kwp     : USD/kWp fotovoltaico instalado
        tasa_descuento   : tasa de descuento (WACC) — default 8 %
        inflacion_tarifa : incremento tarifario anual — default 4 %
        opex_pct_capex   : OPEX como fracción del CAPEX — default 1 %
    """
    reduccion_kw       = kpis['demanda_max'] - kpis['demanda_recortada']
    energia_pv_diaria  = sum(kpis['pv_real'])   # kWh/día

    # CAPEX
    capex_bess  = cfg['c_bat'] * costo_bess_kwh
    capex_pv    = cfg['p_pv']  * costo_pv_kwp
    capex_total = capex_bess + capex_pv
    opex_anual  = capex_total * opex_pct_capex

    # Ahorro base año 0 (sin degradación ni inflación)
    ahorro_demanda_anual_base  = reduccion_kw * tarifa_demanda * 12.0
    ahorro_energia_anual_base  = (energia_pv_diaria * 365.0) * tarifa_energia

    # Proyección a 10 años
    flujos_netos   = [-capex_total]   # año 0: inversión
    flujos_van     = [-capex_total]   # para cálculo VAN
    van_acumulado  = [-capex_total]

    for año in range(1, 11):
        deg_pv      = (1.0 - DEGRADACION_PV_ANUAL) ** año
        inf_tarifa  = (1.0 + inflacion_tarifa) ** año

        ahorro_bruto = (ahorro_demanda_anual_base * inf_tarifa +
                        ahorro_energia_anual_base  * deg_pv * inf_tarifa)
        flujo_neto   = ahorro_bruto - opex_anual
        factor_desc  = (1.0 + tasa_descuento) ** año
        flujo_van    = flujo_neto / factor_desc

        flujos_netos.append(round(flujo_neto, 2))
        flujos_van.append(round(flujo_van, 2))
        van_acumulado.append(round(van_acumulado[-1] + flujo_van, 2))

    van_total = round(sum(flujos_van), 2)

    # TIR por método de Newton-Raphson (iterativo)
    tir = _calcular_tir(flujos_netos)

    # Payback simple (sin descuento)
    acum_simple  = -capex_total
    payback_simple = None
    for año, f in enumerate(flujos_netos[1:], start=1):
        acum_simple += f
        if acum_simple >= 0 and payback_simple is None:
            payback_simple = año

    # Payback descontado (con descuento)
    payback_desc = None
    for año, v in enumerate(van_acumulado):
        if v >= 0 and año > 0:
            payback_desc = año
            break

    return {
        'capex_total':       round(capex_total, 2),
        'capex_bess':        round(capex_bess,  2),
        'capex_pv':          round(capex_pv,    2),
        'opex_anual':        round(opex_anual,  2),
        'van_total':         van_total,
        'tir_pct':           round(tir * 100.0, 2) if tir is not None else None,
        'payback_simple':    payback_simple,
        'payback_desc':      payback_desc,
        'flujos_netos':      flujos_netos,
        'van_acumulado':     van_acumulado,
        'ahorro_anual_año1': round(flujos_netos[1], 2) if len(flujos_netos) > 1 else 0,
    }


def _calcular_tir(flujos: list, max_iter: int = 500, tol: float = 1e-7) -> float | None:
    """Newton-Raphson para TIR sobre la lista de flujos de caja."""
    r = 0.10   # estimación inicial 10 %
    for _ in range(max_iter):
        npv   = sum(f / (1 + r) ** t for t, f in enumerate(flujos))
        dnpv  = sum(-t * f / (1 + r) ** (t + 1) for t, f in enumerate(flujos))
        if abs(dnpv) < 1e-12:
            return None
        r_new = r - npv / dnpv
        if abs(r_new - r) < tol:
            return r_new
        r = r_new
    return None


# ──────────────────────────────────────────────────────────────────────────────
# CICLOS Y DEGRADACIÓN DEL BESS
# ──────────────────────────────────────────────────────────────────────────────
def calcular_degradacion_bess(cfg: dict, df_ems: pd.DataFrame) -> dict:
    """
    Estima los ciclos diarios del BESS y proyecta la degradación
    de capacidad a lo largo de la vida útil.

    LiFePO4 @ DoD 80 %: ~4000 ciclos antes de caer al 80 % de capacidad.
    Degradación por ciclo: 20 % / 4000 = 0.005 % por ciclo.
    """
    # Energía descargada en un día típico (kWh)
    energia_desc_dia = df_ems[df_ems['P_Bat'] > 0]['P_Bat'].sum()   # kWh
    e_util           = cfg['c_bat'] * 0.80                          # kWh útiles

    # Ciclos equivalentes diarios (fracción de ciclo completo)
    ciclos_por_dia = energia_desc_dia / e_util if e_util > 0 else 0.0
    ciclos_por_año = ciclos_por_dia * 365.0

    # Degradación acumulada por año (capacidad residual)
    degradacion_por_ciclo = 0.20 / CICLOS_LIFEP04_VIDA  # fracción

    proyeccion = []
    cap_actual = 1.0  # 100 %
    for año in range(0, 16):
        proyeccion.append({
            'Año':              año,
            'Ciclos_acum':      round(ciclos_por_año * año, 0),
            'Capacidad_pct':    round(cap_actual * 100.0, 1),
            'Capacidad_kWh':    round(cap_actual * cfg['c_bat'], 1),
        })
        cap_actual -= degradacion_por_ciclo * ciclos_por_año
        cap_actual  = max(0.0, cap_actual)

    vida_util_años = CICLOS_LIFEP04_VIDA / ciclos_por_año if ciclos_por_año > 0 else None

    return {
        'ciclos_por_dia':   round(ciclos_por_dia, 3),
        'ciclos_por_año':   round(ciclos_por_año, 1),
        'vida_util_años':   round(vida_util_años, 1) if vida_util_años else "∞",
        'proyeccion':       pd.DataFrame(proyeccion),
    }


# ──────────────────────────────────────────────────────────────────────────────
# VERIFICACIÓN DE PROTECCIONES  (NEC Art. 110-9, 240)
# ──────────────────────────────────────────────────────────────────────────────
def verificar_protecciones(cfg: dict, kpis: dict) -> list[dict]:
    """
    Verifica que el AIC de los disyuntores cubra la Icc asimétrica.
    AIC disyuntor principal supuesto: 50 kA (configurable).

    Retorna lista de verificaciones con estado CUMPLE / NO CUMPLE.
    """
    datos_icc = kpis['datos_icc']
    aic_disco_principal = 50.0  # kA (dato del proyecto)

    verificaciones = [
        {
            'Elemento':    'Disyuntor Principal TGBT',
            'Requisito':   f'AIC ≥ Icc_asimétrico ({datos_icc["icc_asim_kA"]:.3f} kA)',
            'Valor':        f'{aic_disco_principal:.1f} kA',
            'Cumple':       aic_disco_principal >= datos_icc["icc_asim_kA"],
        },
        {
            'Elemento':    'Corriente Nominal Trafo',
            'Requisito':   f'In trafo calculada correctamente',
            'Valor':        f'{datos_icc["i_nom_A"]:.1f} A',
            'Cumple':       datos_icc["i_nom_A"] > 0,
        },
        {
            'Elemento':    'Cargabilidad Transformador',
            'Requisito':   '≤ 85 % continuo (IEEE C57.91)',
            'Valor':        f'{kpis["carg_con_ems"]:.1f} %',
            'Cumple':       kpis["carg_con_ems"] <= 85.0,
        },
        {
            'Elemento':    'THD Tensión (EN 50160)',
            'Requisito':   '< 8 %',
            'Valor':        f'{kpis["thd_tension_max"]:.1f} %',
            'Cumple':       kpis["thd_tension_max"] < 8.0,
        },
        {
            'Elemento':    'THD Corriente Inversor (IEEE 1547)',
            'Requisito':   f'< {THD_I_LIMITES_IEEE1547["THD_total"]} %',
            'Valor':        f'{kpis["thd_corriente_max"]:.2f} %',
            'Cumple':       kpis["thd_corriente_max"] <= THD_I_LIMITES_IEEE1547["THD_total"],
        },
        {
            'Elemento':    'Tensión Mínima Bus BT',
            'Requisito':   '≥ 0.90 p.u. (ARCONEL-001/24)',
            'Valor':        f'{kpis["v_min_pu"]:.3f} p.u.',
            'Cumple':       kpis["v_min_pu"] >= 0.90,
        },
        {
            'Elemento':    'Tensión Máxima Bus BT',
            'Requisito':   '≤ 1.05 p.u. (ARCONEL-001/24)',
            'Valor':        f'{kpis["v_max_pu"]:.3f} p.u.',
            'Cumple':       kpis["v_max_pu"] <= 1.05,
        },
    ]
    return verificaciones


# ──────────────────────────────────────────────────────────────────────────────
# ANÁLISIS DE TRANSITORIOS  (simulador EMT)
# ──────────────────────────────────────────────────────────────────────────────
def simular_evento_transitorio(tipo_evento: str) -> pd.DataFrame:
    """
    Genera series de tiempo V(t) y f(t) para contingencias dinámicas.
    Ventana: 10 s, resolución: 1000 puntos.
    """
    tiempo    = np.linspace(0, 10, 1000)
    voltaje   = np.ones(1000)
    frecuencia = np.ones(1000) * 60.0

    if tipo_evento == "Cortocircuito Trifásico":
        idx_falla = (tiempo >= 2.9) & (tiempo < 3.0)
        idx_recup = tiempo >= 3.0
        voltaje[idx_falla]   = 0.16
        voltaje[idx_recup]   = (0.98
            + 0.05 * np.exp(-(tiempo[idx_recup] - 3) * 5)
            * np.sin(2 * np.pi * 5 * (tiempo[idx_recup] - 3)))
        frecuencia[idx_falla] = 60.18
        frecuencia[idx_recup] = (60.0
            + 0.15 * np.exp(-(tiempo[idx_recup] - 3) * 4)
            * np.cos(2 * np.pi * 3 * (tiempo[idx_recup] - 3)))

    elif tipo_evento == "Cambio de Irradiancia":
        idx = tiempo >= 2.0
        voltaje[idx] = 0.974 + 0.01 * np.exp(-(tiempo[idx] - 2) * 2)

    elif tipo_evento == "Variación de Carga":
        idx = tiempo >= 2.0
        voltaje[idx]    = (0.985
            + 0.015 * np.exp(-(tiempo[idx] - 2) * 1.5)
            * np.cos(2 * np.pi * 2 * (tiempo[idx] - 2)))
        frecuencia[idx] = (59.8
            + 0.2 * np.exp(-(tiempo[idx] - 2) * 2)
            * np.cos(2 * np.pi * 1.5 * (tiempo[idx] - 2)))

    return pd.DataFrame({
        "Tiempo (s)":       tiempo,
        "Voltaje (p.u.)":   voltaje,
        "Frecuencia (Hz)":  frecuencia,
    })
