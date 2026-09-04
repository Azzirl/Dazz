import streamlit as st
import streamlit.components.v1 as components

# Configuración de página a pantalla completa
st.set_page_config(
    page_title="Suite EMS - UPS Bloque D",
    layout="wide",
    page_icon="⚡",
    initial_sidebar_state="collapsed"
)

# Estilo para eliminar márgenes de Streamlit
st.markdown("""
<style>
    .block-container { padding: 0rem !important; }
    header { visibility: hidden; display: none; }
    footer { visibility: hidden; display: none; }
    #MainMenu { visibility: hidden; display: none; }
    iframe { border: none !important; }
</style>
""", unsafe_allow_html=True)

# Aplicación embebida en React 18 con diseño ejecutivo
react_app_html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Suite EMS Bloque D</title>
    <script src="https://unpkg.com/react@18/umd/react.production.min.js" crossorigin></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.production.min.js" crossorigin></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    
    <style>
        :root {
            --bg-color: #f8fafc;
            --surface-1: #ffffff;
            --surface-2: #f1f5f9;
            --text-primary: #0f172a;
            --text-secondary: #475569;
            --text-muted: #94a3b8;
            --text-success: #059669;
            --text-danger: #dc2626;
            --text-warning: #d97706;
            --text-accent: #2563eb;
            --border: #e2e8f0;
            --border-accent: #2563eb;
            --bg-accent: #eff6ff;
            --bg-danger: #fef2f2;
            --border-danger: #fecaca;
            --bg-success: #ecfdf5;
            --border-success: #a7f3d0;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.07);
        }

        * { box-sizing: border-box; }

        body {
            margin: 0;
            padding: 20px 28px;
            background-color: var(--bg-color);
            color: var(--text-primary);
            font-family: var(--font-sans);
            width: 100%;
            overflow-x: hidden;
        }

        input[type="range"] {
            accent-color: #2563eb;
            cursor: pointer;
            height: 6px;
        }

        pre, code {
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
        }

        .card {
            background: var(--surface-1);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 16px;
            box-shadow: var(--shadow-sm);
        }

        .badge {
            display: inline-flex;
            align-items: center;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }

        .badge-blue { background: #dbeafe; color: #1e40af; }
        .badge-green { background: #d1fae5; color: #065f46; }
        .badge-slate { background: #f1f5f9; color: #334155; }
    </style>
</head>
<body>
    <div id="root"></div>

    <script type="text/babel">
        const { useState, useEffect, useRef } = React;

        const REAL_DATA = {
          hourly_load: [36,36,36,36,36,40,60,90,120,145,160,175,179.1,140,150,155,160,165,172,175,130,90,50,36],
          pv_base: [0,0,0,0,0,0,5,25,55,90,120,140,150,140,120,90,55,25,5,0,0,0,0,0],
          quality: {
            thd_u1:1.6, thd_u2:1.9, thd_u3:2.2,
            plt1_max:1.12, plt2_max:1.06, plt3_max:1.08,
            v_nom:127, freq_med:"59.98–60.02",
            deseq:"0.45–0.82", fp_min:0.63,
            i_max_l1:691.2, i_max_l3:263.4, i_neutral:204.3
          },
          irradiation_gye: [1.2,1.4,1.8,2.5,3.2,3.8,4.1,4.3,4.2,3.9,3.2,2.1,1.8,1.5,1.2,0.9,0.5,0.2,0,0,0,0,0,0]
        };

        const COLORS = {
          blue:"#2563eb", orange:"#f97316", green:"#10b981",
          yellow:"#f59e0b", red:"#ef4444", gray:"#64748b",
          violet:"#8b5cf6", teal:"#0d9488"
        };

        function runEMS(loadArr, pvArr, pLim, cBat, cargaNocturna) {
          const socMin = 0.20 * cBat, socMax = cBat;
          let energia = cBat * 0.50;
          const rows = [];
          for (let i = 0; i < 24; i++) {
            const pTeorica = loadArr[i] - pvArr[i];
            let pBat = 0;
            if (pTeorica > pLim) {
              const req = pTeorica - pLim;
              pBat = (energia - req) >= socMin ? req : Math.max(0, energia - socMin);
            } else if (i >= 1 && i <= 5) {
              pBat = (energia + cargaNocturna) <= socMax ? -cargaNocturna : -(socMax - energia);
            }
            const pRed = pTeorica - pBat;
            energia -= pBat;
            const soc = (energia / cBat) * 100;
            rows.push({ hora: `${i.toString().padStart(2,"0")}:00`, pCarga: loadArr[i], pPV: pvArr[i], pBat: +pBat.toFixed(1), pRed: +pRed.toFixed(1), energia: +energia.toFixed(1), soc: +soc.toFixed(1) });
          }
          return rows;
        };

        const MODULES = ["Configuración & Control","Diagrama Unifilar","EMS & Peak Shaving","Calidad de Energía","Dimensionamiento FV+BESS","Comparador Real vs Sim","Memoria Técnica","Código MATLAB / ETAP"];

        function MetricCard({ label, value, unit, sub, color }) {
          return (
            <div className="card">
              <div style={{ fontSize:12, color:"var(--text-secondary)", marginBottom:6, fontWeight:500 }}>{label}</div>
              <div style={{ fontSize:26, fontWeight:700, color: color||"var(--text-primary)", letterSpacing:"-0.5px" }}>{value}<span style={{ fontSize:13, marginLeft:4, color:"var(--text-muted)", fontWeight:400 }}>{unit}</span></div>
              {sub && <div style={{ fontSize:11, color:"var(--text-muted)", marginTop:4, fontWeight:500 }}>{sub}</div>}
            </div>
          );
        }

        function MiniChart({ data, labels, colors, height=140 }) {
          const canvasRef = useRef(null);
          useEffect(() => {
            const canvas = canvasRef.current; if (!canvas) return;
            const ctx = canvas.getContext("2d");
            const W = canvas.offsetWidth, H = height;
            canvas.width = W * window.devicePixelRatio; canvas.height = H * window.devicePixelRatio;
            ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
            ctx.clearRect(0,0,W,H);
            const allVals = data.flat(); const maxV = Math.max(...allVals)*1.1||1; const minV = Math.min(0,...allVals);
            const padL=32, padR=12, padT=12, padB=22;
            const W2=W-padL-padR, H2=H-padT-padB;
            ctx.strokeStyle="#f1f5f9"; ctx.lineWidth=1;
            [0,0.25,0.5,0.75,1].forEach(t=>{
              const y=padT+H2*(1-t);
              ctx.beginPath(); ctx.moveTo(padL,y); ctx.lineTo(padL+W2,y); ctx.stroke();
              ctx.fillStyle="#94a3b8"; ctx.font="10px sans-serif"; ctx.textAlign="right";
              ctx.fillText(Math.round(maxV*t),padL-4,y+3);
            });
            const n = labels.length;
            data.forEach((series, si) => {
              ctx.beginPath(); ctx.strokeStyle=colors[si]||COLORS.blue; ctx.lineWidth=2.5;
              series.forEach((v,i) => {
                const x=padL+W2*(i/(n-1)), y=padT+H2*(1-(v-minV)/(maxV-minV));
                i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
              });
              ctx.stroke();
            });
            ctx.fillStyle="#94a3b8"; ctx.font="10px sans-serif"; ctx.textAlign="center";
            [0,6,12,18,23].forEach(i => ctx.fillText(labels[i], padL+W2*(i/(n-1)), H-4));
          }, [data, labels, colors, height]);
          return <canvas ref={canvasRef} style={{ width:"100%", height }} />;
        }

        function SLD({ params }) {
          const { vNom=220, sTrafo=1000, pLim=130, cBat=250, pPV=150 } = params;
          const iNom = (sTrafo*1000)/(1.73205*vNom);
          const zp = 5.75;
          const icc = (iNom/(zp/100)/1000).toFixed(2);
          const invKva = (pPV/0.95).toFixed(0);
          const eUtil = (cBat*0.80).toFixed(0);

          const Box = ({ x, y, w, h, fill="#E6F1FB", stroke="#185FA5", children }) => (
            <g><rect x={x} y={y} width={w} height={h} fill={fill} stroke={stroke} strokeWidth="1.5" rx="5"/>{children}</g>
          );
          const Txt = ({ x, y, s=10, bold=false, color="#0C447C", children }) => (
            <text x={x} y={y} fontSize={s} fontWeight={bold?"600":"400"} fill={color} textAnchor="middle">{children}</text>
          );
          const Line = ({ x1,y1,x2,y2,color="#333",w=2 }) => <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={w}/>;

          return (
            <svg viewBox="0 0 800 520" style={{ width:"100%", border:"1px solid var(--border)", borderRadius:10, background:"var(--surface-1)", boxShadow:"var(--shadow-sm)" }}>
              <Txt x={400} y={22} s={12} bold color="#0f172a">DIAGRAMA UNIFILAR JERÁRQUICO — SISTEMA EMS BLOQUE D (IEEE 2030.7 / 1547)</Txt>
              <Line x1={400} y1={30} x2={400} y2={60} color="#64748b"/>
              <Box x={260} y={60} w={280} h={48} fill="#eff6ff" stroke="#2563eb">
                <Txt x={400} y={78} s={11} bold color="#1e40af">ACOMETIDA RED PRINCIPAL CNEL — 69 kV / 13.8 kV</Txt>
                <Txt x={400} y={94} s={9.5} color="#2563eb">3F-3H · 60 Hz · Apartarrayos 12 kV</Txt>
              </Box>
              <Line x1={400} y1={108} x2={400} y2={130} color="#64748b"/>
              <circle cx={400} cy={140} r={16} fill="none" stroke="#2563eb" strokeWidth={2}/>
              <circle cx={400} cy={160} r={16} fill="none" stroke="#2563eb" strokeWidth={2}/>
              <Txt x={400} y={144} s={10} color="#2563eb">Δ</Txt>
              <Txt x={400} y={164} s={10} color="#2563eb">Y</Txt>
              <Box x={480} y={125} w={240} h={66} fill="#f0f9ff" stroke="#0284c7">
                <Txt x={600} y={144} s={10} bold color="#0369a1">TRANSFORMADOR PEDESTAL {sTrafo} kVA</Txt>
                <Txt x={600} y={158} s={9} color="#334155">Primario: 69 kV / 13.8 kV (Delta)</Txt>
                <Txt x={600} y={170} s={9} color="#334155">Secundario: {vNom}/127 V (3F-4H, Dyn11)</Txt>
                <Txt x={600} y={182} s={8.5} color="#b91c1c">In={iNom.toFixed(0)} A · Icc_sim={icc} kA (Z%=5.75%)</Txt>
              </Box>
              <Line x1={400} y1={176} x2={400} y2={196} color="#64748b"/>
              <rect x={382} y={196} width={36} height={20} fill="white" stroke="#334155" strokeWidth={1.5} rx={2}/>
              <Txt x={400} y={210} s={9} bold color="#334155">ITM</Txt>
              <Txt x={510} y={208} s={9} color="#15803d" bold>DISYUNTOR TGBT: 3P-2000A · 50 kA AIC</Txt>
              <Line x1={400} y1={216} x2={400} y2={235} color="#64748b"/>
              <Line x1={100} y1={235} x2={700} y2={235} color="#2563eb" w={5}/>
              <Txt x={400} y={228} s={9.5} bold color="#1e3a8a">TABLERO GENERAL DE DISTRIBUCIÓN (TGBT) — BUS {vNom}/127V · 3F-4H</Txt>
              <Line x1={220} y1={235} x2={220} y2={265} color="#64748b"/>
              <rect x={202} y={265} width={36} height={18} fill="white" stroke="#334155" strokeWidth={1.2} rx={2}/>
              <Txt x={220} y={278} s={8} color="#334155">3P</Txt>
              <Line x1={220} y1={283} x2={220} y2={305} color="#ef4444" w={1.5}/>
              <Box x={130} y={305} w={180} h={60} fill="#fef2f2" stroke="#ef4444">
                <Txt x={220} y={323} s={9.5} bold color="#991b1b">CARGAS BLOQUE D (UPS)</Txt>
                <Txt x={220} y={338} s={8.5} color="#334155">Demanda Pico: 179.1 kW</Txt>
                <Txt x={220} y={352} s={8.5} color="#334155">Carga Base: 36.0 kW</Txt>
              </Box>
              <Line x1={580} y1={235} x2={580} y2={265} color="#64748b"/>
              <rect x={562} y={265} width={36} height={18} fill="white" stroke="#334155" strokeWidth={1.2} rx={2}/>
              <Txt x={580} y={278} s={8} color="#334155">3P</Txt>
              <Line x1={580} y1={283} x2={580} y2={305} color="#8b5cf6" w={1.5}/>
              <Box x={488} y={305} w={184} h={60} fill="#faf5ff" stroke="#a855f7">
                <Txt x={580} y={323} s={9.5} bold color="#6b21a8">INVERSOR HÍBRIDO MULTIMODO</Txt>
                <Txt x={580} y={338} s={8.5} color="#334155">S_nom={invKva} kVA · FP=0.95</Txt>
                <Txt x={580} y={352} s={8.5} color="#6b21a8" bold>Control EMS Set-point: {pLim} kW</Txt>
              </Box>
              <Line x1={540} y1={365} x2={540} y2={395} color="#f97316" w={1.5}/>
              <Line x1={620} y1={365} x2={620} y2={395} color="#10b981" w={1.5}/>
              <Box x={485} y={395} w={110} h={60} fill="#fefce8" stroke="#eab308">
                <Txt x={540} y={414} s={9} bold color="#854d0e">ARREGLO PV</Txt>
                <Txt x={540} y={428} s={8.5} color="#334155">{pPV} kWp</Txt>
                <Txt x={540} y={442} s={8} color="#64748b">Módulos PERC 550W</Txt>
              </Box>
              <Box x={605} y={395} w={115} h={60} fill="#ecfdf5" stroke="#10b981">
                <Txt x={662} y={414} s={9} bold color="#065f46">BANCO BESS LiFePO4</Txt>
                <Txt x={662} y={428} s={8.5} color="#334155">{cBat} kWh (512V)</Txt>
                <Txt x={662} y={442} s={8} color="#64748b">E_util: {eUtil} kWh (80%DoD)</Txt>
              </Box>
              <Box x={80} y={465} w={640} h={46} fill="#f8fafc" stroke="#cbd5e1">
                <Txt x={400} y={484} s={8.5} bold color="#334155">PARÁMETROS OPERATIVOS DEL SISTEMA</Txt>
                <Txt x={400} y={498} s={8} color="#64748b">
                  P_lim={pLim} kW · BESS={cBat} kWh · PV={pPV} kWp · V={vNom} V · Trafo={sTrafo} kVA · Icc={icc} kA
                </Txt>
              </Box>
            </svg>
          );
        }

        function TabBar({ tabs, active, onSelect }) {
          return (
            <div style={{ display:"flex", flexWrap:"wrap", gap:8, marginBottom:20, background:"var(--surface-1)", padding:6, borderRadius:10, border:"1px solid var(--border)", boxShadow:"var(--shadow-sm)" }}>
              {tabs.map((t,i) => (
                <button key={i} onClick={()=>onSelect(i)} style={{
                  padding:"9px 16px", fontSize:12, borderRadius:7,
                  border: active===i ? "1px solid var(--border-accent)" : "1px solid transparent",
                  background: active===i ? "var(--bg-accent)" : "transparent",
                  color: active===i ? "var(--text-accent)" : "var(--text-secondary)",
                  cursor:"pointer", fontWeight: active===i ? 600 : 500,
                  transition: "all 0.15s ease-in-out"
                }}>{t}</button>
              ))}
            </div>
          );
        }

        function SliderControl({ label, val, setVal, min, max, step=1, unit }) {
          return (
            <div className="card" style={{ padding:14 }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
                <span style={{ fontSize:12, color:"var(--text-secondary)", fontWeight:600 }}>{label}</span>
                <span style={{ fontSize:13, fontWeight:700, color:"var(--text-accent)", background:"var(--bg-accent)", padding:"2px 8px", borderRadius:6 }}>
                  {val} <span style={{ fontSize:11, fontWeight:500, color:"var(--text-secondary)" }}>{unit}</span>
                </span>
              </div>
              <input type="range" min={min} max={max} step={step} value={val}
                onChange={e=>setVal(+e.target.value)} style={{ width:"100%" }} />
              <div style={{ display:"flex", justifyContent:"space-between", fontSize:10, color:"var(--text-muted)", marginTop:4 }}>
                <span>{min} {unit}</span>
                <span>{max} {unit}</span>
              </div>
            </div>
          );
        }

        function App() {
          const [mod, setMod] = useState(0);
          const [pLim, setPLim] = useState(130);
          const [cBat, setCBat] = useState(250);
          const [pPV, setPPV] = useState(150);
          const [vNom, setVNom] = useState(220);
          const [sTrafo, setSTrafo] = useState(1000);
          const [cargaNoc, setCargaNoc] = useState(40);
          const [showExport, setShowExport] = useState(false);

          const factor = pPV / 150;
          const pvArr = REAL_DATA.pv_base.map(v => +(v * factor).toFixed(1));
          const emsData = runEMS(REAL_DATA.hourly_load, pvArr, pLim, cBat, cargaNoc);
          const horas = emsData.map(r => r.hora);
          const demPico = Math.max(...emsData.map(r => r.pCarga));
          const redPico = Math.max(...emsData.map(r => r.pRed));
          const reduccion = (demPico - redPico).toFixed(1);
          const iNom = (sTrafo * 1000) / (1.73205 * vNom);
          const icc = iNom / (5.75 / 100);
          const cargSin = (demPico / sTrafo * 100).toFixed(1);
          const cargCon = (redPico / sTrafo * 100).toFixed(1);
          const invKva = (pPV / 0.95).toFixed(1);
          const eUtil = (cBat * 0.80).toFixed(0);
          const socMin = (cBat * 0.20).toFixed(0);
          const numMod = Math.ceil((pPV * 1000) / 550);
          const areaMod = (numMod * 2.2).toFixed(0);
          const energiaDia = (REAL_DATA.irradiation_gye.reduce((a,b)=>a+b,0) * pPV * 0.80).toFixed(0);

          const renderMatlabCode = () => `%% ============================================================
%% EMS Peak Shaving — UPS Bloque D
%% Generado automáticamente por Suite EMS Tesis
%% Normas: IEEE 2030.7-2017 / IEEE 1547-2018
%% ============================================================
clear; clc; close all;

%% Parámetros del sistema
P_lim    = ${pLim};       % Límite red [kW]
C_bat    = ${cBat};      % Capacidad BESS [kWh]
P_PV     = ${pPV};       % Potencia PV instalada [kWp]
V_nom    = ${vNom};        % Tensión nominal BT [V]
S_trafo  = ${sTrafo};    % Potencia trafo [kVA]
Z_trafo  = 5.75;          % Impedancia trafo [%]
FP_inv   = 0.95;          % Factor de potencia inversor

%% Datos medidos Bloque D
P_carga = [${REAL_DATA.hourly_load.join(", ")}]; % [kW] 24h
P_PV_base = [${REAL_DATA.pv_base.join(", ")}];    % [kW] perfil FV base

%% Escalar perfil FV según potencia instalada
factor_PV = P_PV / 150;
P_PV_real = P_PV_base * factor_PV;

%% Algoritmo EMS determinístico (Peak Shaving + BESS)
SOC_min = 0.20 * C_bat;
SOC_max = C_bat;
E_bat   = zeros(1,24);
P_bat   = zeros(1,24);
P_red   = zeros(1,24);
SOC     = zeros(1,24);
E_act   = C_bat * 0.50; % Estado inicial 50%

for t = 1:24
    P_teo = P_carga(t) - P_PV_real(t);
    P_b   = 0;
    if P_teo > P_lim
        req = P_teo - P_lim;
        if (E_act - req) >= SOC_min
            P_b = req;
        else
            P_b = max(0, E_act - SOC_min);
        end
    elseif t >= 2 && t <= 6
        if (E_act + ${cargaNoc}) <= SOC_max
            P_b = -${cargaNoc};
        else
            P_b = -(SOC_max - E_act);
        end
    end
    E_act     = E_act - P_b;
    P_bat(t)  = P_b;
    P_red(t)  = P_teo - P_b;
    E_bat(t)  = E_act;
    SOC(t)    = (E_act / C_bat) * 100;
end

%% Cálculos normativos
In_BT  = (S_trafo * 1000) / (sqrt(3) * V_nom);
Icc    = In_BT / (Z_trafo/100);
S_inv  = P_PV / FP_inv;
E_util = C_bat * 0.80;

fprintf('=== RESULTADOS EMS ===\\n');
fprintf('Demanda pico original : %.1f kW\\n', max(P_carga));
fprintf('Demanda pico recortada: %.1f kW\\n', max(P_red));
fprintf('Reducción de pico     : %.1f kW\\n', max(P_carga)-max(P_red));
fprintf('Icc transformador     : %.2f kA\\n', Icc/1000);
fprintf('Corriente nominal BT  : %.1f A\\n', In_BT);
fprintf('Potencia inversor     : %.1f kVA\\n', S_inv);
fprintf('Energía útil BESS     : %.1f kWh\\n', E_util);
`;

          const renderETAPInstructions = () => `=== GUÍA DE MODELADO EN ETAP ===
Proyecto: Sistema EMS Bloque D — UPS GYE
Fecha: ${new Date().toLocaleDateString()}

1. CONFIGURACIÓN GENERAL
   - Frecuencia: 60 Hz | Base kVA: ${sTrafo} kVA | Base kV: ${vNom/1000} kV

2. ELEMENTOS A MODELAR
   a) Red CNEL: Fuente infinita 13.8 kV, SCC = 500 MVA
   b) Transformador pedestal: ${sTrafo} kVA, 13.8 kV / ${vNom/1000} kV, Dyn11 (%Z = 5.75%, Icc = ${(icc/1000).toFixed(2)} kA)
   c) Bus TGBT: ${vNom} V, 3F+N
   d) Inversor Solar (PVS): ${invKva} kVA, FP = 0.95 inductivo
   e) Sistema PV: ${pPV} kWp (${numMod} módulos PERC 550 Wp)
   f) BESS: ${cBat} kWh, 512 V DC (LiFePO4, C-rate 0.5C)

3. PROTECCIONES & ESTUDIOS
   - Disyuntor principal: 3P-2000A, Icu = 50 kA (NEC Art. 110-9)
   - Estudios: Load Flow (Newton-Raphson), Short Circuit (ANSI Std 141/399), Arc Flash (IEEE 1584).
`;

          const renderMemoria = () => `
MEMORIA TÉCNICA Y ESPECIFICACIONES DE PROYECTO
═══════════════════════════════════════════════════════════════
Proyecto: Sistema EMS Peak Shaving — Bloque D (UPS GYE)
Código: GPS-EMS-UPSD-MTC-001  Rev. C
Fecha: ${new Date().toLocaleDateString()}
Normas: IEEE 2030.7-2017 | IEEE 1547-2018 | EN 50160 | NEC Art.110-9
═══════════════════════════════════════════════════════════════

1. OBJETIVOS
   Diseñar y validar un Sistema EMS de Peak Shaving para el
   Edificio D (UPS Guayaquil), limitando la demanda a la red a
   ${pLim} kW mediante un BESS de ${cBat} kWh y sistema FV de ${pPV} kWp.

2. SISTEMA DE POTENCIA EXISTENTE
   Transformador pedestal: ${sTrafo} kVA, 13.8kV/220V, Dyn11, Z%=5.75%
   · Corriente nominal BT: ${iNom.toFixed(1)} A
   · Icc simétrica:        ${(icc/1000).toFixed(2)} kA
   · Cargabilidad orig.:   ${cargSin}%  →  Con EMS: ${cargCon}%
   · Disyuntor principal:  3P-2000A, 50 kA AIC (NEC Art.110-9 ✓)

3. DIMENSIONAMIENTO FOTOVOLTAICO Y BESS
   · Potencia pico PV:     ${pPV} kWp (${numMod} módulos PERC 550 Wp, ${areaMod} m²)
   · Energía diaria GYE:   ~${energiaDia} kWh/día (HPS=4.3 h)
   · Capacidad BESS:       ${cBat} kWh (LiFePO4, 512 V DC)
   · Energía útil (DoD80): ${eUtil} kWh (SOC_min = ${socMin} kWh)

4. RESULTADOS DE SIMULACIÓN EMS
   · Demanda pico original:  ${demPico.toFixed(1)} kW
   · Demanda pico recortada: ${redPico.toFixed(1)} kW
   · Reducción de pico:      ${reduccion} kW (${((parseFloat(reduccion)/demPico)*100).toFixed(1)}%)
   · Cargabilidad trafo:     ${cargSin}% → ${cargCon}%
`;

          return (
            <div style={{ width:"100%", boxSizing:"border-box" }}>
              {/* BANNER TÍTULO E INFORMACIÓN EJECUTIVA */}
              <div style={{ background:"var(--surface-1)", padding:"16px 20px", borderRadius:10, border:"1px solid var(--border)", boxShadow:"var(--shadow-sm)", marginBottom:16, display:"flex", justifyContent:"space-between", alignItems:"center", flexWrap:"wrap", gap:12 }}>
                <div>
                  <div style={{ fontSize:18, fontWeight:700, color:"var(--text-primary)", display:"flex", alignItems:"center", gap:10 }}>
                    ⚡ Suite EMS — Gestor de Gestión Energética Bloque D (UPS)
                  </div>
                  <div style={{ fontSize:12, color:"var(--text-secondary)", marginTop:3 }}>
                    Optimización por Peak Shaving · Reducción de Demanda de Red · Cumplimiento IEEE 2030.7 / 1547
                  </div>
                </div>
                <div style={{ display:"flex", gap:8, flexWrap:"wrap" }}>
                  <span className="badge badge-blue">UPS Campus Centenario</span>
                  <span className="badge badge-green">Trafo 1000 kVA</span>
                  <span className="badge badge-slate">P_lim = {pLim} kW</span>
                </div>
              </div>

              <TabBar tabs={MODULES} active={mod} onSelect={setMod} />

              {mod === 0 && (
                <div>
                  <div style={{ fontSize:14, fontWeight:600, marginBottom:12, color:"var(--text-primary)" }}>Panel de Ajuste de Parámetros de Diseño</div>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(280px, 1fr))", gap:12, marginBottom:20 }}>
                    <SliderControl label="Set-point límite de red (P_lim)" val={pLim} setVal={setPLim} min={80} max={200} step={5} unit="kW" />
                    <SliderControl label="Capacidad BESS (C_bat)" val={cBat} setVal={setCBat} min={50} max={600} step={10} unit="kWh" />
                    <SliderControl label="Potencia Fotovoltaica (P_PV)" val={pPV} setVal={setPPV} min={0} max={300} step={10} unit="kWp" />
                    <SliderControl label="Carga nocturna programada BESS" val={cargaNoc} setVal={setCargaNoc} min={10} max={100} step={5} unit="kW" />
                    <SliderControl label="Tensión nominal en Baja Tensión" val={vNom} setVal={setVNom} min={110} max={480} step={10} unit="V" />
                    <SliderControl label="Capacidad del Transformador" val={sTrafo} setVal={setSTrafo} min={315} max={2000} step={50} unit="kVA" />
                  </div>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(3, 1fr)", gap:12 }}>
                    <MetricCard label="Reducción neta de pico" value={reduccion} unit="kW" sub={`Pico original: ${demPico.toFixed(0)} kW → Recortado: ${redPico.toFixed(0)} kW`} color="var(--text-success)" />
                    <MetricCard label="Corriente Cortocircuito Icc" value={(icc/1000).toFixed(2)} unit="kA" sub="Cálculo simétrico en bus 220V (%Z=5.75)" />
                    <MetricCard label="Cargabilidad del Transformador" value={cargCon} unit="%" sub={`Sin EMS: ${cargSin}% de carga térmica`} />
                  </div>
                </div>
              )}

              {mod === 1 && (
                <div>
                  <SLD params={{ vNom, sTrafo, pLim, cBat, pPV }} />
                  <div style={{ marginTop:10, fontSize:11, color:"var(--text-muted)", textAlign:"center" }}>
                    Esquema unifilar vectorial dinámico — responde automáticamente a los ajustes del panel de control
                  </div>
                </div>
              )}

              {mod === 2 && (
                <div>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(3, 1fr)", gap:12, marginBottom:16 }}>
                    <MetricCard label="Demanda pico bruta original" value={demPico.toFixed(1)} unit="kW" />
                    <MetricCard label="Demanda pico real desde red" value={redPico.toFixed(1)} unit="kW" color="var(--text-success)" />
                    <MetricCard label="Ahorro de demanda (Peak Shaving)" value={reduccion} unit="kW" sub={((parseFloat(reduccion)/demPico)*100).toFixed(1)+"% aplanado"} color="var(--text-accent)" />
                  </div>
                  <div style={{ marginBottom:8, fontSize:13, fontWeight:600, color:"var(--text-secondary)" }}>Perfiles de Potencia Activa (24 Horas)</div>
                  <MiniChart
                    data={[emsData.map(r=>r.pCarga), emsData.map(r=>r.pPV), emsData.map(r=>r.pRed)]}
                    labels={horas}
                    colors={[COLORS.blue, COLORS.yellow, COLORS.red]}
                    height={160} />
                  <div style={{ display:"flex", gap:20, fontSize:12, color:"var(--text-secondary)", margin:"8px 0 16px" }}>
                    <span style={{ display:"flex", alignItems:"center", gap:6 }}><span style={{ width:12, height:3, background:COLORS.blue, display:"inline-block", borderRadius:2 }}></span>Demanda Bruta Bloque D</span>
                    <span style={{ display:"flex", alignItems:"center", gap:6 }}><span style={{ width:12, height:3, background:COLORS.yellow, display:"inline-block", borderRadius:2 }}></span>Generación PV</span>
                    <span style={{ display:"flex", alignItems:"center", gap:6 }}><span style={{ width:12, height:3, background:COLORS.red, display:"inline-block", borderRadius:2 }}></span>Potencia Consumida de Red</span>
                  </div>
                  <div style={{ marginBottom:8, fontSize:13, fontWeight:600, color:"var(--text-secondary)" }}>Estado de Carga BESS (SOC %)</div>
                  <MiniChart data={[emsData.map(r=>r.soc)]} labels={horas} colors={[COLORS.teal]} height={110} />
                  <div style={{ marginTop:16, overflowX:"auto" }}>
                    <table style={{ width:"100%", fontSize:12, borderCollapse:"collapse", background:"var(--surface-1)", borderRadius:8, border:"1px solid var(--border)" }}>
                      <thead>
                        <tr style={{ borderBottom:"1px solid var(--border)", background:"var(--surface-2)" }}>
                          {["Hora","P_Carga (kW)","P_PV (kW)","P_Batería (kW)","P_Red Real (kW)","Energía BESS (kWh)","SOC (%)"].map(h=>(
                            <th key={h} style={{ padding:"8px 10px", textAlign:"center", color:"var(--text-secondary)", fontWeight:600 }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {emsData.map((r,i) => (
                          <tr key={i} style={{ borderBottom:"1px solid var(--border)", background: r.pRed > pLim ? "var(--bg-warning)" : "transparent" }}>
                            <td style={{ padding:"6px 10px", textAlign:"center", fontWeight:600 }}>{r.hora}</td>
                            <td style={{ padding:"6px 10px", textAlign:"right" }}>{r.pCarga}</td>
                            <td style={{ padding:"6px 10px", textAlign:"right", color:COLORS.yellow, fontWeight:500 }}>{r.pPV}</td>
                            <td style={{ padding:"6px 10px", textAlign:"right", color: r.pBat>0?COLORS.orange:COLORS.teal, fontWeight:600 }}>{r.pBat}</td>
                            <td style={{ padding:"6px 10px", textAlign:"right", color: r.pRed>pLim?COLORS.red:COLORS.green, fontWeight:700 }}>{r.pRed}</td>
                            <td style={{ padding:"6px 10px", textAlign:"right" }}>{r.energia}</td>
                            <td style={{ padding:"6px 10px", textAlign:"right", fontWeight:600 }}>{r.soc}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {mod === 3 && (
                <div>
                  <div style={{ fontSize:14, fontWeight:600, marginBottom:12 }}>Resumen de Calidad de Energía — Medidor METREL MI2792</div>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(3, 1fr)", gap:10, marginBottom:16 }}>
                    <MetricCard label="THD U1 (Voltaje)" value="1.6" unit="%" sub="< 8% Norma EN 50160" color="var(--text-success)" />
                    <MetricCard label="THD U2 (Voltaje)" value="1.9" unit="%" sub="< 8% Cumple" color="var(--text-success)" />
                    <MetricCard label="THD U3 (Voltaje)" value="2.2" unit="%" sub="< 8% Cumple" color="var(--text-success)" />
                    <MetricCard label="Flicker PLT1" value="1.12" unit="" sub="> 1.0 Alerta de parpadeo" color="var(--text-danger)" />
                    <MetricCard label="Flicker PLT2" value="1.06" unit="" sub="> 1.0 Alerta" color="var(--text-danger)" />
                    <MetricCard label="Flicker PLT3" value="1.08" unit="" sub="> 1.0 Alerta" color="var(--text-danger)" />
                    <MetricCard label="Desequilibrio de Fase" value="0.45–0.82" unit="%" sub="< 2% Cumple" color="var(--text-success)" />
                    <MetricCard label="Frecuencia de Red" value="59.98–60.02" unit="Hz" sub="Estable" color="var(--text-success)" />
                    <MetricCard label="Factor de Potencia Mínimo" value="0.63" unit="" sub="Registrado en la noche" color="var(--text-warning)" />
                  </div>
                  <div style={{ background:"var(--bg-danger)", border:"1px solid var(--border-danger)", borderRadius:8, padding:"12px 16px", marginBottom:16 }}>
                    <div style={{ fontSize:13, fontWeight:600, color:"var(--text-danger)", marginBottom:4 }}>Aviso Técnico: Inconformidad en Flicker (Plt > 1.0)</div>
                    <div style={{ fontSize:12, color:"var(--text-secondary)", lineHeight:1.5 }}>
                      Las mediciones de campo muestran variaciones rápidas de carga que elevan el índice Plt por encima de los límites de la norma EN 50160. Se recomienda que el inversor del BESS opere con control activo de potencia reactiva (EVC) para estabilizar el voltaje del nodo.
                    </div>
                  </div>
                </div>
              )}

              {mod === 4 && (
                <div>
                  <div style={{ fontSize:14, fontWeight:600, marginBottom:12 }}>Dimensionamiento de Componentes FV + BESS</div>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(2, 1fr)", gap:10, marginBottom:16 }}>
                    <MetricCard label="Módulos Fotovoltaicos Requeridos" value={numMod} unit="uds." sub="Módulos PERC Monocristalinos 550 Wp" />
                    <MetricCard label="Área Estimada de Cubierta" value={areaMod} unit="m²" sub="Calculado a 2.2 m² por panel" />
                    <MetricCard label="Energía Generada Diaria Estimada" value={energiaDia} unit="kWh/día" sub="HPS promedio Guayaquil: 4.3 h" />
                    <MetricCard label="Capacidad del Inversor Híbrido" value={invKva} unit="kVA" sub="S_nom calculada a FP = 0.95" />
                    <MetricCard label="Capacidad Útil BESS (DoD 80%)" value={eUtil} unit="kWh" sub="Energía efectiva utilizable" />
                    <MetricCard label="Reserva de Seguridad BESS (20%)" value={socMin} unit="kWh" sub="Protección química del banco" />
                  </div>
                </div>
              )}

              {mod === 5 && (
                <div>
                  <div style={{ fontSize:14, fontWeight:600, marginBottom:12 }}>Comparativa: Mediciones de Campo vs Simulación EMS</div>
                  <div style={{ display:"grid", gridTemplateColumns:"repeat(3, 1fr)", gap:10, marginBottom:16 }}>
                    <MetricCard label="Demanda Pico Medida" value="179.1" unit="kW" sub="Analizador METREL MI2792" />
                    <MetricCard label="Demanda Pico Simulada EMS" value={redPico.toFixed(1)} unit="kW" color="var(--text-success)" sub="Con gestión BESS/PV" />
                    <MetricCard label="Efectividad de Recorte" value={Math.abs(((parseFloat(reduccion)/demPico)*100)).toFixed(1)} unit="%" color="var(--text-accent)" sub="Reducción de demanda de pico" />
                  </div>
                  <div style={{ fontSize:13, fontWeight:600, color:"var(--text-secondary)", marginBottom:8 }}>Comparativa Horaria de la Curva de Demanda</div>
                  <MiniChart
                    data={[REAL_DATA.hourly_load, emsData.map(r=>r.pRed)]}
                    labels={horas}
                    colors={[COLORS.blue, COLORS.green]}
                    height={160} />
                </div>
              )}

              {mod === 6 && (
                <div>
                  <div style={{ fontSize:14, fontWeight:600, marginBottom:12 }}>Resumen Ejecutivo de la Memoria Técnica</div>
                  <pre style={{ fontSize:11, lineHeight:1.6, background:"var(--surface-1)", border:"1px solid var(--border)", borderRadius:8, padding:"16px 20px", overflowX:"auto", color:"var(--text-primary)", whiteSpace:"pre-wrap", wordBreak:"break-word" }}>
                    {renderMemoria()}
                  </pre>
                </div>
              )}

              {mod === 7 && (
                <div>
                  <TabBar
                    tabs={["Código MATLAB","Guía ETAP"]}
                    active={showExport ? 1 : 0}
                    onSelect={v => setShowExport(v===1)} />
                  {!showExport ? (
                    <pre style={{ fontSize:11, lineHeight:1.6, background:"var(--surface-1)", border:"1px solid var(--border)", borderRadius:8, padding:"16px 20px", overflowX:"auto", color:"var(--text-primary)", whiteSpace:"pre-wrap" }}>
                      {renderMatlabCode()}
                    </pre>
                  ) : (
                    <pre style={{ fontSize:11, lineHeight:1.6, background:"var(--surface-1)", border:"1px solid var(--border)", borderRadius:8, padding:"16px 20px", overflowX:"auto", color:"var(--text-primary)", whiteSpace:"pre-wrap" }}>
                      {renderETAPInstructions()}
                    </pre>
                  )}
                </div>
              )}
            </div>
          );
        }

        const root = ReactDOM.createRoot(document.getElementById('root'));
        root.render(<App />);
    </script>
</body>
</html>
"""

# Renderizado responsivo a pantalla completa
components.html(react_app_html, height=1100, scrolling=True)
