import pytest
import numpy as np
import sys
import os

# Asegurar que se puedan importar los módulos locales
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.ems_math import calcular_soporte_reactivo

def test_soporte_reactivo_caida_tension():
    """Prueba que el inversor inyecte reactivos cuando el voltaje cae de 0.98 p.u."""
    v_actual = 0.95
    p_activa = 50.0
    s_inv = 158.0
    
    q_inyectada, v_corregido = calcular_soporte_reactivo(v_actual, p_activa, s_inv)
    
    assert q_inyectada > 0, "El sistema debe inyectar reactivos ante una caída de tensión"
    assert v_corregido > v_actual, "El voltaje corregido debe ser mayor al voltaje de falla"

def test_soporte_reactivo_sobre_tension():
    """Prueba que el inversor absorba reactivos cuando el voltaje sube de 1.02 p.u."""
    v_actual = 1.04
    p_activa = 50.0
    s_inv = 158.0
    
    q_inyectada, v_corregido = calcular_soporte_reactivo(v_actual, p_activa, s_inv)
    
    assert q_inyectada < 0, "El sistema debe absorber reactivos ante una sobretensión"
    assert v_corregido < v_actual, "El voltaje corregido debe ser menor al voltaje de falla"
