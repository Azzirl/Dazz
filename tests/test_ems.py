import pytest
from core.ems_math import calcular_balance_24h, calcular_soporte_reactivo, calcular_icc

def test_limite_soc_minimo():
    cfg = {
        'nombre_proyecto': 'Test',
        'ubicacion_proyecto': 'UPS',
        'p_lim': 80.0,
        'c_bat': 100.0,
        'p_pv': 0.0,
        'v_nom': 220.0,
        's_trafo': 1000.0,
        'carga_noc': 0.0,
        'ps_activo': True,
        'lat': -2.1833,
        'lon': -79.8833
    }
    df_ems, kpis = calcular_balance_24h(cfg)
    assert df_ems['E_BESS_kWh'].min() >= 20.0

def test_control_volt_var_subtension():
    q_iny, v_corr = calcular_soporte_reactivo(v_actual_pu=0.95, p_activa_kw=50.0, s_inv_kva=100.0)
    assert q_iny > 0
    assert v_corr > 0.95

def test_control_volt_var_sobretension():
    q_iny, v_corr = calcular_soporte_reactivo(v_actual_pu=1.04, p_activa_kw=50.0, s_inv_kva=100.0)
    assert q_iny < 0
    assert v_corr < 1.04

def test_calculo_icc():
    icc_dict = calcular_icc(s_trafo_kva=1000.0, v_nom_v=220.0)
    assert icc_dict['icc_sim_kA'] > 0
    assert icc_dict['icc_asim_kA'] > icc_dict['icc_sim_kA']
