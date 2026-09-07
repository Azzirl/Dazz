"""
utils/exports.py — Módulo de exportación de reportes, planos CAD DXF y código MATLAB
"""

def generate_dxf_full(cfg: dict, inv_req: float) -> str:
    """
    Genera el diagrama unifilar en formato CAD DXF (R12 / R2000)
    escalando entidades dinámicamente según la configuración de la microred.
    """
    lines = [
        "0", "SECTION", "2", "HEADER", "0", "ENDSEC",
        "0", "SECTION", "2", "TABLES", "0", "ENDSEC",
        "0", "SECTION", "2", "BLOCKS", "0", "ENDSEC",
        "0", "SECTION", "2", "ENTITIES"
    ]

    def add_line(layer, x1, y1, x2, y2, color="7"):
        lines.extend(["0", "LINE", "8", layer, "62", color,
                      "10", f"{x1:.2f}", "20", f"{y1:.2f}", "30", "0.0",
                      "11", f"{x2:.2f}", "21", f"{y2:.2f}", "31", "0.0"])

    def add_circle(layer, cx, cy, r, color="7"):
        lines.extend(["0", "CIRCLE", "8", layer, "62", color,
                      "10", f"{cx:.2f}", "20", f"{cy:.2f}", "30", "0.0",
                      "40", f"{r:.2f}"])

    def add_text(layer, x, y, text, height=3.0, color="7"):
        lines.extend(["0", "TEXT", "8", layer, "62", color,
                      "10", f"{x:.2f}", "20", f"{y:.2f}", "30", "0.0",
                      "40", f"{height:.2f}", "1", str(text)])

    def add_box(layer, x1, y1, x2, y2, color="7"):
        add_line(layer, x1, y1, x2, y1, color)
        add_line(layer, x2, y1, x2, y2, color)
        add_line(layer, x2, y2, x1, y2, color)
        add_line(layer, x1, y2, x1, y1, color)

    # Marco y Cajetín del Plano
    add_box("MARCO", -200, -150, 300, 250, color="2")
    add_box("CAJETIN", 100, -140, 290, -80, color="2")
    add_text("TEXTOS", 110, -90, f"PROYECTO: {cfg['nombre_proyecto'].upper()}", 4.0, "7")
    add_text("TEXTOS", 110, -105, f"UBICACION: {cfg['ubicacion_proyecto'].upper()}", 3.5, "7")
    add_text("TEXTOS", 110, -120, f"TRAFO: {cfg['s_trafo']:.0f} kVA | V_BT: {cfg['v_nom']:.0f} V", 3.0, "3")
    add_text("TEXTOS", 110, -132, f"INVERSOR IBR: {inv_req:.1f} kVA | BESS: {cfg['c_bat']:.0f} kWh", 3.0, "4")

    # Red CNEL MT (13.8 kV)
    add_line("RED_MT", 50, 220, 50, 160, color="4")
    add_text("TEXTOS", 55, 200, "RED CNEL - 13.8 kV (PCC)", 3.5, "7")

    # Transformador Principal
    add_circle("TRAFO", 50, 140, 15, color="4")
    add_circle("TRAFO", 50, 120, 15, color="4")
    add_text("TEXTOS", 80, 130, f"TRANSFORMADOR {cfg['s_trafo']:.0f} kVA (Z%=5.75%)", 3.5, "7")

    # Bus Principal TGBT (Baja Tensión)
    add_line("BUS", 50, 105, 50, 50, color="4")
    add_line("BUS", -80, 50, 220, 50, color="4")
    add_text("TEXTOS", 30, 58, f"BUS PRINCIPAL TGBT {cfg['v_nom']:.0f}V BT", 4.0, "3")

    # Ramal 1: Cargas Edificio D
    add_line("RED_BT", -40, 50, -40, 10, color="1")
    add_box("EQUIPOS", -60, -10, -20, 10, color="1")
    add_text("TEXTOS", -55, -2, "CARGAS BLOQUE D", 3.0, "7")
    add_text("TEXTOS", -55, -8, "P_max = 179.1 kW", 2.5, "1")

    # Ramal 2: Inversor de Potencia IBR
    add_line("RED_BT", 140, 50, 140, 10, color="6")
    add_box("EQUIPOS", 100, -10, 180, 10, color="6")
    add_text("TEXTOS", 105, -2, f"INVERSOR IBR {inv_req:.1f} kVA", 3.0, "7")
    add_text("TEXTOS", 105, -8, "Control Volt/VAR IEEE 2800", 2.5, "6")

    # Bus DC y Fuentes Renovables
    add_line("RED_DC", 120, -10, 120, -40, color="2")
    add_box("EQUIPOS", 100, -60, 140, -40, color="2")
    add_text("TEXTOS", 105, -52, f"ARREGLO PV {cfg['p_pv']:.0f} kWp", 2.8, "7")

    add_line("RED_DC", 160, -10, 160, -40, color="3")
    add_box("EQUIPOS", 140, -60, 180, -40, color="3")
    add_text("TEXTOS", 145, -52, f"BESS {cfg['c_bat']:.0f} kWh", 2.8, "7")

    lines.extend(["0", "ENDSEC", "0", "EOF"])
    return "\n".join(lines)


def generar_codigo_matlab(cfg: dict, kpis: dict) -> str:
    """
    Genera el script ejecutable de MATLAB (.m) coincidente
    con la lógica corregida de core/ems_math.py.
    """
    inv_k = kpis.get('inv_kva', kpis.get('inv_req', 157.9))
    matlab_code = f"""%% ============================================================
%% Simulación Energética y Peak Shaving EMS — {cfg['nombre_proyecto']}
%% Universidad Politécnica Salesiana — Campus Centenario (Bloque D)
%% ============================================================
clear; clc; close all;

%% 1. PARÁMETROS DEL SISTEMA Y TRANSFORMADOR
P_lim        = {cfg['p_lim']:.2f};      % Set-point límite red (kW)
S_trafo      = {cfg['s_trafo']:.2f};    % Capacidad nominal trafo (kVA)
V_nom        = {cfg['v_nom']:.2f};      % Tensión nominal BT (V)
C_bat        = {cfg['c_bat']:.2f};      % Capacidad BESS (kWh)
P_pv_nominal = {cfg['p_pv']:.2f};       % Potencia nominal PV (kWp)
Carga_noc    = {cfg['carga_noc']:.2f};   % Potencia carga nocturna (kW)

% Eficiencias e Impedancias Físicas
eta_sistema  = 0.80;                  % Eficiencia global PV (módulos, cables, temp)
eta_inversor = 0.95;                  % Rendimiento inversor
Z_trafo_pu   = 0.0575;                % Impedancia % (5.75%)
R_trafo_pu   = 0.011;                 % Resistencia % (1.1%)
X_trafo_pu   = sqrt(Z_trafo_pu^2 - R_trafo_pu^2);

S_inv        = {inv_k:.2f};             % Capacidad aparente inversor (kVA)
SOC_min      = 0.20 * C_bat;          % Reserva mínima 20%
Energia      = C_bat * 0.50;          % Estado inicial 50%

%% 2. PERFILES DE ENTRADA (24 Horas)
P_carga = [{', '.join(map(str, kpis.get('REAL_LOAD', [179.1]*24)))}];
G_satelital = [{', '.join(map(str, kpis.get('irradiancia_24h', [0]*24)))}];  % W/m2

%% 3. BUCLE HORARIO DE SIMULACIÓN EMS
P_pv = zeros(1,24);
P_bat = zeros(1,24);
P_red = zeros(1,24);
SOC = zeros(1,24);
V_bus = zeros(1,24);
Q_iny = zeros(1,24);

for t = 1:24
    % Generación Fotovoltaica real en kW (eta_sistema = 0.80)
    P_pv(t) = P_pv_nominal * (G_satelital(t) / 1000.0) * eta_sistema;
    P_teorica = P_carga(t) - P_pv(t);
    
    % Despacho Peak Shaving
    if P_teorica > P_lim
        req = P_teorica - P_lim;
        if (Energia - req) >= SOC_min
            P_bat(t) = req;
        else
            P_bat(t) = max(0, Energia - SOC_min);
        end
    elseif (t >= 2) && (t <= 6)  % Carga nocturna 01:00-05:00
        espacio = C_bat - Energia;
        P_bat(t) = -min(Carga_noc, espacio);
    end
    
    P_red(t) = P_teorica - P_bat(t);
    Energia = max(SOC_min, min(C_bat, Energia - P_bat(t)));
    SOC(t) = (Energia / C_bat) * 100.0;
    
    % Caída de tensión por modelo físico (Z_trafo)
    Q_carga = P_red(t) * 0.30;
    P_pu = P_red(t) / S_trafo;
    Q_pu = Q_carga / S_trafo;
    delta_V = (P_pu * R_trafo_pu) + (Q_pu * X_trafo_pu);
    V_base = max(0.85, 1.0 - delta_V);
    
    % Control Reactivo Volt/VAR (IEEE 2800)
    P_inv_total = abs(P_bat(t)) + P_pv(t);
    Q_max = sqrt(max(0, S_inv^2 - P_inv_total^2));
    
    if V_base < 0.98
        Q_req = (0.98 - V_base) * (S_inv * 2.0);
        Q_iny(t) = min(Q_req, Q_max);
        V_bus(t) = V_base + (Q_iny(t) / (S_inv * 2.0));
    elseif V_base > 1.02
        Q_req = (V_base - 1.02) * (S_inv * 2.0);
        Q_iny(t) = -min(Q_req, Q_max);
        V_bus(t) = V_base + (Q_iny(t) / (S_inv * 2.0));
    else
        V_bus(t) = V_base;
    end
end

%% 4. IMPRESIÓN DE RESULTADOS
fprintf('=====================================================\\n');
fprintf('        RESULTADOS DE LA SIMULACIÓN EMS EN MATLAB   \\n');
fprintf('=====================================================\\n');
fprintf('Demanda Máxima Original:         %.2f kW\\n', max(P_carga));
fprintf('Demanda Máxima Red (Recortada):  %.2f kW\\n', max(P_red));
fprintf('Reducción Pico (Peak Shaving):   %.2f kW (%.1f %%)\\n', max(P_carga)-max(P_red), ((max(P_carga)-max(P_red))/max(P_carga))*100);
fprintf('Cargabilidad Trafo con EMS:      %.1f %%\\n', (max(P_red)/S_trafo)*100);
fprintf('Voltaje Mínimo BT Corregido:     %.3f p.u.\\n', min(V_bus));
fprintf('=====================================================\\n');
"""
    return matlab_code
