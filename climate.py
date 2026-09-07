import requests

def obtener_irradiancia_real(lat=-2.1833, lon=-79.8833):
    """
    Obtiene el perfil de irradiancia solar (W/m2) de 24 horas en tiempo real
    usando la API satelital de Open-Meteo. Incluye un perfil fallback.
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=shortwave_radiation&timezone=auto&forecast_days=1"
    
    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json()
            irradiancia_24h = data['hourly']['shortwave_radiation'][:24] # W/m2
            return irradiancia_24h, True
    except Exception:
        pass
        
    # Perfil solar de respaldo (Fallback) en W/m2 si no hay internet
    irradiancia_fallback = [0, 0, 0, 0, 0, 0, 35, 170, 370, 600, 800, 930, 1000, 930, 800, 600, 370, 170, 35, 0, 0, 0, 0, 0]
    return irradiancia_fallback, False
