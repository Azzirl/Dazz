import numpy as np
import pandas as pd

def calcular_soporte_reactivo(v_actual_pu, p_activa, s_inv_kva):
    """Control de voltaje (Volt/VAR) con curva de droop."""
    q_max = np.sqrt(max(0, s_inv_kva**2 - p_activa**2))
    q_inyectada = 0.0
    v_corregido = v_actual_pu
    
    if v_actual_pu < 0.98:
        q_requerida = (0.98 - v_actual_pu) * (s_inv_kva * 2) 
        q_inyectada = min(q_requerida, q_max)
        v_corregido = v_actual_pu + (q_inyectada / (s_inv_kva * 2))
    elif v_actual_pu > 1.02:
        q_requerida = (v_actual_pu - 1.02) * (s_inv_kva * 2)
        q_inyectada = max(-q_requerida, -q_max)
        v_corregido = v_actual_pu + (q_inyectada / (s_inv_kva * 2))
        
    return q_inyectada, v_corregido

def simular_evento_transitorio(tipo_evento):
    """Generador de series de tiempo para fallas dinámicas."""
    tiempo = np.linspace(0, 10, 1000)
    voltaje = np.ones(1000) * 1.0 
    frecuencia = np.ones(1000) * 60.0 
    
    if tipo_evento == "Cortocircuito Trifásico":
        idx_falla = (tiempo >= 2.9) & (tiempo < 3.0)
        idx_recup = tiempo >= 3.0
        voltaje[idx_falla] = 0.16 
        voltaje[idx_recup] = 0.98 + 0.05 * np.exp(-(tiempo[idx_recup]-3)*5) * np.sin(2*np.pi*5*(tiempo[idx_recup]-3))
        frecuencia[idx_falla] = 60.18
        frecuencia[idx_recup] = 60.0 + 0.15 * np.exp(-(tiempo[idx_recup]-3)*4) * np.cos(2*np.pi*3*(tiempo[idx_recup]-3))
        
    elif tipo_evento == "Cambio de Irradiancia":
        idx_falla = tiempo >= 2.0
        voltaje[idx_falla] = 0.974 + 0.01 * np.exp(-(tiempo[idx_falla]-2)*2)
        
    elif tipo_evento == "Variación de Carga":
        idx_falla = tiempo >= 2.0
        voltaje[idx_falla] = 0.985 + 0.015 * np.exp(-(tiempo[idx_falla]-2)*1.5) * np.cos(2*np.pi*2*(tiempo[idx_falla]-2))
        frecuencia[idx_falla] = 59.8 + 0.2 * np.exp(-(tiempo[idx_falla]-2)*2) * np.cos(2*np.pi*1.5*(tiempo[idx_falla]-2))
        
    return pd.DataFrame({"Tiempo (s)": tiempo, "Voltaje (p.u.)": voltaje, "Frecuencia (Hz)": frecuencia})

def calcular_balance_24h(cfg):
    """Simula el balance energético de 24 horas y retorna los KPIs."""
    REAL_LOAD = [36, 36, 36, 36, 36, 40, 60, 90, 120, 145, 160, 175, 179.1, 140, 150, 155, 160, 165, 172, 175, 130, 90, 50, 36]
    PV_BASE = [0, 0, 0, 0, 0, 0, 5, 25, 55, 90, 120, 140, 150, 140, 120, 90, 55, 25, 5, 0, 0, 0, 0, 0]
    
    factor_pv = cfg['p_pv'] / 150.0 if cfg['p_pv'] > 0 else 0.0
    pv_real = [round(v * factor_pv, 1) for v in PV_BASE]
    
    soc_min = 0.20 * cfg['c_bat']; soc_max = cfg['c_bat']; energia = cfg['c_bat'] * 0.50
    limite_operativo = cfg['p_lim'] if cfg['ps_activo'] else 9999.0
    inv_req = cfg['p_pv'] / 0.95 if cfg['p_pv'] > 0 else cfg['p_lim'] / 0.95

    rows_ems = []
    for i in range(24):
        p_teorica = REAL_LOAD[i] - pv_real[i]
        p_bat = 0.0
        
        if p_teorica > limite_operativo:
            req = p_teorica - limite_operativo
            p_bat = req if (energia - req) >= soc_min else max(0.0, energia - soc_min)
        elif 1 <= i <= 5: 
            p_bat = -cfg['carga_noc'] if (energia + cfg['carga_noc']) <= soc_max else -(soc_max - energia)
            
        p_red = p_teorica - p_bat
        energia -= p_bat
        soc = (energia / cfg['c_bat']) * 100.0
        
        v_base = 1.0 - (p_red / cfg['s_trafo']) * 0.4
        q_inyectada, v_final = calcular_soporte_reactivo(v_base, p_bat + pv_real[i], inv_req)
        
        rows_ems.append({
            'Hora': f"{i:02d}:00", 'P_Carga': REAL_LOAD[i], 'P_PV': pv_real[i], 
            'P_Bat': round(p_bat, 1), 'P_Red': round(p_red, 1), 'SOC': round(soc, 1), 
            'V_pu': round(v_final, 3), 'Q_inyectada': round(q_inyectada, 1)
        })

    df_ems = pd.DataFrame(rows_ems)
    kpis = {
        'demanda_max': float(df_ems['P_Carga'].max()),
        'demanda_recortada': float(df_ems['P_Red'].max()),
        'carg_con': (float(df_ems['P_Red'].max()) / cfg['s_trafo']) * 100.0,
        'inv_req': inv_req,
        'soc_min': soc_min,
        'pv_real': pv_real,
        'REAL_LOAD': REAL_LOAD
    }
    
    return df_ems, kpis
