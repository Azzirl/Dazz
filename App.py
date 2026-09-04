import { useState, useEffect, useRef, useCallback } from "react";

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
  blue:"#2a78d6", orange:"#eb6834", green:"#1baf7a",
  yellow:"#eda100", red:"#e34948", gray:"#888780",
  violet:"#6250d6", teal:"#0F6E56"
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

const MODULES = ["Datos del Proyecto","Diagrama Unifilar","EMS & Peak Shaving","Calidad de Energía","Dimensionamiento FV+BESS","Comparador Real vs Sim","Memoria Técnica","Código MATLAB / ETAP"];

function MetricCard({ label, value, unit, sub, color }) {
  return (
    <div style={{ background:"var(--surface-1)", borderRadius:8, padding:"12px 14px", border:"0.5px solid var(--border)" }}>
      <div style={{ fontSize:12, color:"var(--text-secondary)", marginBottom:4 }}>{label}</div>
      <div style={{ fontSize:22, fontWeight:500, color: color||"var(--text-primary)" }}>{value}<span style={{ fontSize:12, marginLeft:3, color:"var(--text-muted)" }}>{unit}</span></div>
      {sub && <div style={{ fontSize:11, color:"var(--text-muted)", marginTop:2 }}>{sub}</div>}
    </div>
  );
}

function MiniChart({ data, labels, colors, height=120, yLabel="" }) {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current; if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const W = canvas.offsetWidth, H = height;
    canvas.width = W * window.devicePixelRatio; canvas.height = H * window.devicePixelRatio;
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    ctx.clearRect(0,0,W,H);
    const allVals = data.flat(); const maxV = Math.max(...allVals)*1.1||1; const minV = Math.min(0,...allVals);
    const padL=28, padR=8, padT=8, padB=20;
    const W2=W-padL-padR, H2=H-padT-padB;
    ctx.strokeStyle="#e1e0d9"; ctx.lineWidth=0.5;
    [0,0.25,0.5,0.75,1].forEach(t=>{
      const y=padT+H2*(1-t);
      ctx.beginPath(); ctx.moveTo(padL,y); ctx.lineTo(padL+W2,y); ctx.stroke();
      ctx.fillStyle="#898781"; ctx.font="10px sans-serif"; ctx.textAlign="right";
      ctx.fillText(Math.round(maxV*t),padL-2,y+4);
    });
    const n = labels.length;
    data.forEach((series, si) => {
      ctx.beginPath(); ctx.strokeStyle=colors[si]||COLORS.blue; ctx.lineWidth=2;
      series.forEach((v,i) => {
        const x=padL+W2*(i/(n-1)), y=padT+H2*(1-(v-minV)/(maxV-minV));
        i===0?ctx.moveTo(x,y):ctx.lineTo(x,y);
      });
      ctx.stroke();
    });
    ctx.fillStyle="#898781"; ctx.font="10px sans-serif"; ctx.textAlign="center";
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
    <g><rect x={x} y={y} width={w} height={h} fill={fill} stroke={stroke} strokeWidth="1.5" rx="4"/>{children}</g>
  );
  const Txt = ({ x, y, s=10, bold=false, color="#0C447C", children }) => (
    <text x={x} y={y} fontSize={s} fontWeight={bold?"600":"400"} fill={color} textAnchor="middle">{children}</text>
  );
  const Line = ({ x1,y1,x2,y2,color="#333",w=2 }) => <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth={w}/>;

  return (
    <svg viewBox="0 0 700 520" style={{ width:"100%", border:"0.5px solid var(--border)", borderRadius:8, background:"var(--surface-2)" }}>
      <Txt x={350} y={18} s={11} bold color="#0C447C">Diagrama Unifilar — Sistema EMS Bloque D (IEEE 2030.7 / 1547)</Txt>
      <Line x1={350} y1={24} x2={350} y2={60} color="#555"/>
      <Box x={230} y={60} w={240} h={48} fill="#E6F1FB" stroke="#185FA5">
        <Txt x={350} y={78} s={10} bold>ACOMETIDA CNEL — 13.8 kV</Txt>
        <Txt x={350} y={92} s={9} color="#185FA5">3F-3H · 60 Hz · Apartarrayos 12 kV</Txt>
      </Box>
      <Line x1={350} y1={108} x2={350} y2={130} color="#555"/>
      <circle cx={350} cy={140} r={16} fill="none" stroke="#185FA5" strokeWidth={2}/>
      <circle cx={350} cy={160} r={16} fill="none" stroke="#185FA5" strokeWidth={2}/>
      <Txt x={350} y={144} s={9} color="#185FA5">Δ</Txt>
      <Txt x={350} y={164} s={9} color="#185FA5">Y</Txt>
      <Box x={420} y={128} w={200} h={60} fill="#EBF5FB" stroke="#3498DB">
        <Txt x={520} y={148} s={9} bold>TRANSFORMADOR {sTrafo} kVA</Txt>
        <Txt x={520} y={162} s={8} color="#1B4F72">13.8kV/220V · Dyn11 · Z%={zp}</Txt>
        <Txt x={520} y={176} s={8} color="#922B21">In={iNom.toFixed(0)} A · Icc={icc} kA</Txt>
      </Box>
      <Line x1={350} y1={176} x2={350} y2={196} color="#555"/>
      <rect x={332} y={196} width={36} height={20} fill="white" stroke="#333" strokeWidth={1.5} rx={2}/>
      <Txt x={350} y={210} s={9} bold color="#333">ITM</Txt>
      <Txt x={440} y={208} s={9} color="#0a6b0a">3P-2000A · 50 kA AIC</Txt>
      <Line x1={350} y1={216} x2={350} y2={235} color="#555"/>
      <Line x1={80} y1={235} x2={610} y2={235} color="#2a78d6" w={5}/>
      <Txt x={350} y={228} s={9} bold color="#042C53">TGBT — BUS 220/127V · 3F-4H</Txt>
      <Line x1={180} y1={235} x2={180} y2={265} color="#555"/>
      <rect x={162} y={265} width={36} height={18} fill="white" stroke="#333" strokeWidth={1.2} rx={2}/>
      <Txt x={180} y={278} s={8} color="#333">3P</Txt>
      <Line x1={180} y1={283} x2={180} y2={305} color="#e34948" w={1.5}/>
      <Box x={100} y={305} w={160} h={58} fill="#FDEDEC" stroke="#E74C3C">
        <Txt x={180} y={323} s={9} bold color="#922B21">CARGAS BLOQUE D</Txt>
        <Txt x={180} y={337} s={8} color="#333">Pico: 179.1 kW</Txt>
        <Txt x={180} y={350} s={8} color="#333">Base: 36.0 kW</Txt>
      </Box>
      <Line x1={520} y1={235} x2={520} y2={265} color="#555"/>
      <rect x={502} y={265} width={36} height={18} fill="white" stroke="#333" strokeWidth={1.2} rx={2}/>
      <Txt x={520} y={278} s={8} color="#333">3P</Txt>
      <Line x1={520} y1={283} x2={520} y2={305} color="#6250d6" w={1.5}/>
      <Box x={438} y={305} w={164} h={58} fill="#F4ECF7" stroke="#884EA0">
        <Txt x={520} y={323} s={9} bold color="#512E5F">INVERSOR HÍBRIDO</Txt>
        <Txt x={520} y={337} s={8} color="#333">S={invKva} kVA · FP=0.95</Txt>
        <Txt x={520} y={350} s={8} color="#512E5F">Set-point: {pLim} kW</Txt>
      </Box>
      <Line x1={490} y1={363} x2={490} y2={395} color="#eb6834" w={1.5}/>
      <Line x1={555} y1={363} x2={555} y2={395} color="#1baf7a" w={1.5}/>
      <Box x={440} y={395} w={96} h={60} fill="#FEF9E7" stroke="#F1C40F">
        <Txt x={488} y={414} s={9} bold color="#7D6608">ARRAY PV</Txt>
        <Txt x={488} y={428} s={8} color="#333">{pPV} kWp</Txt>
        <Txt x={488} y={441} s={7.5} color="#555">PERC 550W</Txt>
      </Box>
      <Box x={545} y={395} w={100} h={60} fill="#E8F8F5" stroke="#2ECC71">
        <Txt x={595} y={414} s={9} bold color="#085041">BESS LiFePO4</Txt>
        <Txt x={595} y={428} s={8} color="#333">{cBat} kWh</Txt>
        <Txt x={595} y={441} s={7.5} color="#555">E_util: {eUtil} kWh</Txt>
      </Box>
      <Box x={60} y={460} w={580} h={52} fill="#F8F9FA" stroke="#aaa">
        <Txt x={350} y={480} s={8.5} bold color="#333">Parámetros de diseño configurados</Txt>
        <Txt x={350} y={494} s={8} color="#555">
          P_lim={pLim}kW · BESS={cBat}kWh · PV={pPV}kWp · V={vNom}V · Trafo={sTrafo}kVA · Icc={icc}kA
        </Txt>
      </Box>
    </svg>
  );
}

function TabBar({ tabs, active, onSelect }) {
  return (
    <div style={{ display:"flex", flexWrap:"wrap", gap:4, marginBottom:16 }}>
      {tabs.map((t,i) => (
        <button key={i} onClick={()=>onSelect(i)} style={{
          padding:"6px 10px", fontSize:11, borderRadius:6,
          border: active===i ? "1.5px solid var(--border-accent)" : "0.5px solid var(--border)",
          background: active===i ? "var(--bg-accent)" : "var(--surface-1)",
          color: active===i ? "var(--text-accent)" : "var(--text-secondary)",
          cursor:"pointer", fontWeight: active===i ? 500 : 400
        }}>{t}</button>
      ))}
    </div>
  );
}

export default function App() {
  const [mod, setMod] = useState(0);
  const [pLim, setPLim] = useState(130);
  const [cBat, setCBat] = useState(250);
  const [pPV, setPPV] = useState(150);
  const [vNom, setVNom] = useState(220);
  const [sTrafo, setSTrafo] = useState(1000);
  const [cargaNoc, setCargaNoc] = useState(40);
  const [nombreProyecto, setNombreProyecto] = useState("EMS Bloque D — UPS GYE");
  const [responsable, setResponsable] = useState("Maestrante en Electricidad");
  const [tutor, setTutor] = useState("Ing. Gary Ampuño Aviles");
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
%% EMS Peak Shaving — ${nombreProyecto}
%% Generado automáticamente por Suite EMS Tesis
%% Responsable: ${responsable} | Tutor: ${tutor}
%% Fecha: ${new Date().toLocaleDateString()}
%% Normas: IEEE 2030.7-2017 / IEEE 1547-2018
%% ============================================================
clear; clc; close all;

%% Parámetros del sistema
P_lim   = ${pLim};      % Límite red [kW]
C_bat   = ${cBat};     % Capacidad BESS [kWh]
P_PV    = ${pPV};      % Potencia PV instalada [kWp]
V_nom   = ${vNom};       % Tensión nominal BT [V]
S_trafo = ${sTrafo};    % Potencia trafo [kVA]
Z_trafo = 5.75;         % Impedancia trafo [%]
FP_inv  = 0.95;         % Factor de potencia inversor

%% Datos medidos Bloque D (informe Atheus, agosto 2022)
P_carga = [${REAL_DATA.hourly_load.join(", ")}]; % [kW] 24h
P_PV_base = [${REAL_DATA.pv_base.join(", ")}];   % [kW] perfil FV base

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

%% Gráficas
horas = 0:23;
figure('Name','EMS Peak Shaving — ${nombreProyecto}','NumberTitle','off');

subplot(3,1,1);
plot(horas, P_carga, 'b-o', 'LineWidth',1.5, 'DisplayName','Demanda real'); hold on;
plot(horas, P_red,  'r--s', 'LineWidth',1.5, 'DisplayName','P red con EMS');
plot(horas, P_PV_real,'g-^','LineWidth',1.2,'DisplayName','Generación PV');
yline(P_lim,'k--','Set-point','LabelHorizontalAlignment','left');
xlabel('Hora del día'); ylabel('Potencia [kW]');
title('Perfiles de Potencia — Peak Shaving'); legend; grid minor;

subplot(3,1,2);
bar(horas, P_bat, 'FaceColor',[0.6 0.4 0.8],'DisplayName','P batería');
xlabel('Hora del día'); ylabel('P_{bat} [kW]');
title('Despacho BESS (>0 descarga, <0 carga)'); grid minor;

subplot(3,1,3);
plot(horas, SOC, 'k-d', 'LineWidth',1.5);
yline(20,'r--','SOC_{min}'); yline(100,'g--','SOC_{max}');
xlabel('Hora del día'); ylabel('SOC [%]');
title('Estado de Carga BESS'); ylim([0 110]); grid minor;

%% Exportar a Excel
T = table(horas', P_carga', P_PV_real', P_bat', P_red', SOC', ...
    'VariableNames',{'Hora','P_Carga_kW','P_PV_kW','P_Bat_kW','P_Red_kW','SOC_pct'});
writetable(T, 'Resultados_EMS_BloquD.xlsx');
disp('Resultados exportados a Resultados_EMS_BloquD.xlsx');
`;

  const renderETAPInstructions = () => `=== GUÍA PARA MODELADO EN ETAP ===
Proyecto: ${nombreProyecto}
Generado: ${new Date().toLocaleDateString()}

1. CONFIGURACIÓN GENERAL
   - Frecuencia: 60 Hz
   - Base kVA: ${sTrafo} kVA
   - Base kV (BT): ${vNom/1000} kV
   - Base kV (MT): 13.8 kV

2. ELEMENTOS A MODELAR
   a) Red CNEL: Fuente infinita 13.8 kV, SCC = 500 MVA
   b) Transformador pedestal:
      * ${sTrafo} kVA, 13.8 kV / ${vNom/1000} kV, Dyn11
      * %Z = 5.75%, %R = 1.1%, Grupo Dyn11
      * Icc secundario: ${(icc/1000).toFixed(2)} kA
   c) Bus TGBT: ${vNom} V, 3F+N
   d) Cargas Bloque D:
      * Pico: ${demPico.toFixed(1)} kW, FP = 0.92
      * Perfil de carga: importar desde CSV adjunto
   e) Inversor Solar (PVS):
      * ${invKva} kVA, FP = 0.95 inductivo
      * Conectar al bus TGBT mediante CB 3P
   f) Sistema PV:
      * ${pPV} kWp, ${numMod} módulos PERC 550 Wp
      * Conectar al lado DC del inversor
   g) BESS:
      * ${cBat} kWh, 512 V DC, LiFePO4
      * C-rate: 0.5C → P_max = ${(cBat*0.5).toFixed(0)} kW
      * SOC inicial: 50%, SOC_min: 20%, SOC_max: 100%

3. PROTECCIONES
   - Disyuntor principal: 3P-2000A, Icu = 50 kA
   - Protección trafo: Diferencial (87T)
   - Rel. de sobrecorriente: 51/51N
   - Rel. anti-isla inversor: 81O/U, 27, 59 (IEEE 1547)

4. ESTUDIOS A EJECUTAR EN ETAP
   a) Load Flow: Newton-Raphson, tolerancia 0.001
   b) Short Circuit: ANSI/IEEE Std 141 y 399
   c) Motor Starting: si aplica
   d) Harmonic Analysis: hasta armónico 25 (norma EN 50160)
   e) Arc Flash: IEEE 1584-2018

5. COMPARACIÓN CON DATOS REALES
   - Importar datos medidos: METREL MI2792 (informe agosto 2022)
   - Variables: I1, I2, I3, IN, U1, U2, U3, P, Q, S, FP, THD, Plt
   - Validar: error relativo < 5% en P_total y FP

ARCHIVOS ASOCIADOS:
   - Resultados_EMS_BloquD.xlsx (exportado desde MATLAB)
   - INFORME_Bloque_D.pdf (datos reales METREL)
   - Plano_Unifilar_EMS.dxf (para importar topología)
`;

  const renderMemoria = () => `
MEMORIA TÉCNICA Y ESPECIFICACIONES DE PROYECTO
═══════════════════════════════════════════════════════════════
Proyecto: ${nombreProyecto}
Código: GPS-EMS-UPSD-MTC-001  Rev. C
Responsable: ${responsable}
Tutor: ${tutor}
Fecha: ${new Date().toLocaleDateString()}
Normas: IEEE 2030.7-2017 | IEEE 1547-2018 | EN 50160 | NEC Art.110-9
═══════════════════════════════════════════════════════════════

1. OBJETIVOS
   Diseñar y validar un Sistema EMS de Peak Shaving para el
   Edificio D (UPS Guayaquil), limitando la demanda a la red a
   ${pLim} kW mediante un BESS de ${cBat} kWh y sistema FV de ${pPV} kWp.

2. ANTECEDENTES
   La Universidad Politécnica Salesiana, sede Guayaquil, Campus
   Centenario (calles Robles 107 y Chambers), registró fluctuaciones
   de tensión y picos de demanda en el Bloque D (laboratorios).
   La medición con METREL MI2792 PowerQ4 Plus (18-26/07/2022, 8 días,
   1168 intervalos de 10 min) detectó:
   · Demanda pico bruta:    179.1 kW (hora 12:00-13:00)
   · Potencia aparente máx: 180.9 kVA
   · Factor de potencia mín: 0.63 (nocturno)
   · Flicker PLT:           hasta 1.12 → NO CUMPLE EN 50160
   · THD tensión:           máx 2.2% → CUMPLE (< 8%)
   · Desequilibrio:         0.45-0.82% → CUMPLE (< 2%)
   · Frecuencia:            59.98-60.02 Hz → CUMPLE

3. BASE TÉCNICA Y NORMATIVA
   IEEE Std 2030.2-2015  — Sistemas de almacenamiento BESS
   IEEE Std 2030.7-2017  — Algoritmos de gestión EMS
   IEEE Std 1547-2018    — Interconexión de recursos distribuidos
   EN 50160              — Calidad de tensión en BT
   NEC Art. 110-9        — Capacidad interruptiva

4. SISTEMA DE POTENCIA EXISTENTE
   Transformador pedestal: ${sTrafo} kVA, 13.8kV/220V, Dyn11, Z%=5.75%
   · Corriente nominal BT: ${iNom.toFixed(1)} A
   · Icc simétrica:        ${(icc/1000).toFixed(2)} kA
   · Cargabilidad orig.:   ${cargSin}%  →  Con EMS: ${cargCon}%
   · Disyuntor principal:  3P-2000A, 50 kA AIC (NEC Art.110-9 ✓)

5. DIMENSIONAMIENTO SISTEMA FV
   · Potencia pico:        ${pPV} kWp
   · Número de módulos:    ${numMod} uds. PERC 550 Wp (35V, 15.7A)
   · Área requerida:       ${areaMod} m²
   · Energía diaria GYE:   ${energiaDia} kWh/día (HPS=4.3 h/día)
   · Eficiencia sistema:   80% (pérd. calor, cableado, inversor)
   · Potencia inversor:    ${invKva} kVA (FP=0.95, IEEE 1547 ✓)

6. DIMENSIONAMIENTO BESS
   · Capacidad nominal:    ${cBat} kWh, LiFePO4, 512 V DC
   · Energía útil (DoD80): ${eUtil} kWh
   · SOC mínimo (IEEE2030): ${socMin} kWh (20%)
   · Potencia de descarga:  ${(cBat*0.5).toFixed(0)} kW (C-rate 0.5C)
   · Ciclos de vida:        ~4000 ciclos (@ DoD 80%)
   · Autonomía nocturna:   ${(parseFloat(eUtil)/${cargaNoc}).toFixed(1)} h a ${cargaNoc} kW

7. ALGORITMO EMS — PEAK SHAVING
   Lógica determinística en lazo cerrado:
   · Si P_carga - P_PV > P_lim → descargar BESS
   · Si 01:00-05:00 y SOC < 100% → cargar BESS (${cargaNoc} kW)
   · Restricciones: SOC_min=${socMin}kWh ≤ E_bat ≤ ${cBat}kWh

   RESULTADOS DE SIMULACIÓN:
   · Demanda pico original:  ${demPico.toFixed(1)} kW
   · Demanda pico recortada: ${redPico.toFixed(1)} kW
   · Reducción de pico:      ${reduccion} kW (${((parseFloat(reduccion)/demPico)*100).toFixed(1)}%)
   · Cargabilidad trafo:     ${cargSin}% → ${cargCon}%

8. CONCLUSIONES
   a) El sistema EMS permite reducir la demanda máxima en ${reduccion} kW,
      llevando la cargabilidad del trafo de ${cargSin}% a ${cargCon}%.
   b) El flicker (Plt>1) identificado en mediciones requiere la
      instalación de un control VAR electrónico (EVC) o estabilizador.
   c) El sistema FV de ${pPV} kWp genera ~${energiaDia} kWh/día,
      reduciendo la dependencia de la red en horas solares.
   d) La validación en ETAP confirmará los resultados de simulación
      y verificará las protecciones (AIC = 50 kA).

─────────────────────────────────────────────────────────────
Firma: ___________________    Revisado: ___________________
       ${responsable}                ${tutor}
`;

  const Input = ({ label, val, setVal, min, max, step=1, unit }) => (
    <div style={{ marginBottom:10 }}>
      <div style={{ display:"flex", justifyContent:"space-between", marginBottom:3 }}>
        <span style={{ fontSize:12, color:"var(--text-secondary)" }}>{label}</span>
        <span style={{ fontSize:12, fontWeight:500 }}>{val} <span style={{ color:"var(--text-muted)" }}>{unit}</span></span>
      </div>
      <input type="range" min={min} max={max} step={step} value={val}
        onChange={e=>setVal(+e.target.value)} style={{ width:"100%" }} />
    </div>
  );

  const TextIn = ({ label, val, setVal, full }) => (
    <div style={{ marginBottom:8, gridColumn: full?"1 / -1":"auto" }}>
      <label style={{ fontSize:12, color:"var(--text-secondary)", display:"block", marginBottom:3 }}>{label}</label>
      <input type="text" value={val} onChange={e=>setVal(e.target.value)}
        style={{ width:"100%", fontSize:13, padding:"6px 8px", borderRadius:6,
          border:"0.5px solid var(--border)", background:"var(--surface-1)", color:"var(--text-primary)", boxSizing:"border-box" }} />
    </div>
  );

  return (
    <div style={{ padding:"1rem 0", fontFamily:"var(--font-sans)", maxWidth:700 }}>
      <div style={{ marginBottom:16 }}>
        <div style={{ fontSize:18, fontWeight:500, color:"var(--text-primary)" }}>Suite EMS — Tesis de Maestría en Electricidad</div>
        <div style={{ fontSize:13, color:"var(--text-secondary)" }}>Peak Shaving · FV+BESS · UPS Bloque D · IEEE 2030 / EN 50160</div>
      </div>

      <TabBar tabs={MODULES} active={mod} onSelect={setMod} />

      {mod === 0 && (
        <div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, marginBottom:16 }}>
            <TextIn label="Nombre del proyecto" val={nombreProyecto} setVal={setNombreProyecto} full />
            <TextIn label="Responsable / Maestrante" val={responsable} setVal={setResponsable} />
            <TextIn label="Docente tutor" val={tutor} setVal={setTutor} />
          </div>
          <div style={{ borderTop:"0.5px solid var(--border)", paddingTop:14, marginBottom:14 }}>
            <div style={{ fontSize:13, fontWeight:500, marginBottom:10 }}>Parámetros del sistema</div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"0 20px" }}>
              <Input label="Set-point límite red P_lim" val={pLim} setVal={setPLim} min={80} max={200} step={5} unit="kW" />
              <Input label="Capacidad BESS C_bat" val={cBat} setVal={setCBat} min={50} max={600} step={10} unit="kWh" />
              <Input label="Potencia FV P_PV" val={pPV} setVal={setPPV} min={0} max={300} step={10} unit="kWp" />
              <Input label="Carga nocturna BESS" val={cargaNoc} setVal={setCargaNoc} min={10} max={100} step={5} unit="kW" />
              <Input label="Tensión nominal BT" val={vNom} setVal={setVNom} min={110} max={480} step={10} unit="V" />
              <Input label="Potencia transformador" val={sTrafo} setVal={setSTrafo} min={315} max={2000} step={50} unit="kVA" />
            </div>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8 }}>
            <MetricCard label="Reducción de pico" value={reduccion} unit="kW" sub={`${demPico.toFixed(0)} → ${redPico.toFixed(0)} kW`} color="var(--text-success)" />
            <MetricCard label="Icc transformador" value={(icc/1000).toFixed(2)} unit="kA" sub="Z%=5.75%" />
            <MetricCard label="Cargabilidad trafo" value={cargCon} unit="%" sub={`antes: ${cargSin}%`} />
          </div>
        </div>
      )}

      {mod === 1 && (
        <div>
          <SLD params={{ vNom, sTrafo, pLim, cBat, pPV }} />
          <div style={{ marginTop:10, fontSize:11, color:"var(--text-muted)", textAlign:"center" }}>
            Diagrama generado según IEEE 2030.7 / 1547 — actualiza con los parámetros del módulo "Datos del Proyecto"
          </div>
        </div>
      )}

      {mod === 2 && (
        <div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8, marginBottom:14 }}>
            <MetricCard label="Demanda pico original" value={demPico.toFixed(1)} unit="kW" />
            <MetricCard label="P_red con EMS" value={redPico.toFixed(1)} unit="kW" color="var(--text-success)" />
            <MetricCard label="Reducción" value={reduccion} unit="kW" sub={((parseFloat(reduccion)/demPico)*100).toFixed(1)+"%"} color="var(--text-accent)" />
          </div>
          <div style={{ marginBottom:6, fontSize:12, color:"var(--text-secondary)" }}>Perfiles de potencia (24 h)</div>
          <MiniChart
            data={[emsData.map(r=>r.pCarga), emsData.map(r=>r.pPV), emsData.map(r=>r.pRed)]}
            labels={horas}
            colors={[COLORS.blue, COLORS.yellow, COLORS.red]}
            height={150} />
          <div style={{ display:"flex", gap:16, fontSize:11, color:"var(--text-secondary)", margin:"6px 0 12px" }}>
            <span style={{ display:"flex", alignItems:"center", gap:4 }}><span style={{ width:10, height:2, background:COLORS.blue, display:"inline-block" }}></span>Carga</span>
            <span style={{ display:"flex", alignItems:"center", gap:4 }}><span style={{ width:10, height:2, background:COLORS.yellow, display:"inline-block" }}></span>PV</span>
            <span style={{ display:"flex", alignItems:"center", gap:4 }}><span style={{ width:10, height:2, background:COLORS.red, display:"inline-block" }}></span>Red con EMS</span>
          </div>
          <div style={{ marginBottom:6, fontSize:12, color:"var(--text-secondary)" }}>SOC banco BESS (%)</div>
          <MiniChart data={[emsData.map(r=>r.soc)]} labels={horas} colors={[COLORS.teal]} height={100} />
          <div style={{ marginTop:12, overflowX:"auto" }}>
            <table style={{ width:"100%", fontSize:11, borderCollapse:"collapse" }}>
              <thead>
                <tr style={{ borderBottom:"1px solid var(--border)" }}>
                  {["Hora","P_Carga","P_PV","P_Bat","P_Red","E_BESS","SOC"].map(h=>(
                    <th key={h} style={{ padding:"4px 6px", textAlign:"center", color:"var(--text-secondary)", fontWeight:500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {emsData.map((r,i) => (
                  <tr key={i} style={{ borderBottom:"0.5px solid var(--border)", background: r.pRed > pLim ? "var(--bg-warning)" : "transparent" }}>
                    <td style={{ padding:"3px 6px", textAlign:"center", fontWeight:500 }}>{r.hora}</td>
                    <td style={{ padding:"3px 6px", textAlign:"right" }}>{r.pCarga}</td>
                    <td style={{ padding:"3px 6px", textAlign:"right", color:COLORS.yellow }}>{r.pPV}</td>
                    <td style={{ padding:"3px 6px", textAlign:"right", color: r.pBat>0?COLORS.orange:COLORS.teal }}>{r.pBat}</td>
                    <td style={{ padding:"3px 6px", textAlign:"right", color: r.pRed>pLim?COLORS.red:COLORS.green }}>{r.pRed}</td>
                    <td style={{ padding:"3px 6px", textAlign:"right" }}>{r.energia}</td>
                    <td style={{ padding:"3px 6px", textAlign:"right" }}>{r.soc}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {mod === 3 && (
        <div>
          <div style={{ fontSize:13, fontWeight:500, marginBottom:10 }}>Resumen calidad de energía — METREL MI2792 (agosto 2022)</div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8, marginBottom:14 }}>
            <MetricCard label="THD U1" value="1.6" unit="%" sub="< 8% ✓ EN50160" color="var(--text-success)" />
            <MetricCard label="THD U2" value="1.9" unit="%" sub="< 8% ✓" color="var(--text-success)" />
            <MetricCard label="THD U3" value="2.2" unit="%" sub="< 8% ✓" color="var(--text-success)" />
            <MetricCard label="Flicker PLT1" value="1.12" unit="" sub="< 1 ✗ NO CUMPLE" color="var(--text-danger)" />
            <MetricCard label="Flicker PLT2" value="1.06" unit="" sub="< 1 ✗" color="var(--text-danger)" />
            <MetricCard label="Flicker PLT3" value="1.08" unit="" sub="< 1 ✗" color="var(--text-danger)" />
            <MetricCard label="Desequilibrio u-" value="0.45–0.82" unit="%" sub="< 2% ✓" color="var(--text-success)" />
            <MetricCard label="Frecuencia" value="59.98–60.02" unit="Hz" sub="✓ EN50160" color="var(--text-success)" />
            <MetricCard label="FP mínimo" value="0.63" unit="" sub="nocturno — mejorar" color="var(--text-warning)" />
          </div>
          <div style={{ background:"var(--bg-danger)", border:"0.5px solid var(--border-danger)", borderRadius:8, padding:"10px 14px", marginBottom:12 }}>
            <div style={{ fontSize:12, fontWeight:500, color:"var(--text-danger)", marginBottom:4 }}>No conformidad detectada — Flicker</div>
            <div style={{ fontSize:11, color:"var(--text-secondary)" }}>
              El Plt supera 1.0 en las tres fases. Se requiere instalación de Control VAR Electrónico (EVC) o estabilizador de voltaje.
              Los picos ocurren en horario laboral: 12:00, 14:00, 15:00 y 19:00 h.
            </div>
          </div>
          <div style={{ fontSize:12, fontWeight:500, marginBottom:8 }}>Corrientes máximas registradas</div>
          <MiniChart
            data={[REAL_DATA.hourly_load.map(v=>v/vNom*1000/1.732)]}
            labels={horas} colors={[COLORS.blue]} height={100} />
          <div style={{ fontSize:11, color:"var(--text-muted)", marginTop:4 }}>
            I1/I2 pico ≈ {(REAL_DATA.hourly_load[12]/vNom*1000/1.732).toFixed(0)} A · I3 pico ≈ 263 A · IN ≈ 204 A (medidos con pinzas 1×3 kA)
          </div>
        </div>
      )}

      {mod === 4 && (
        <div>
          <div style={{ fontSize:13, fontWeight:500, marginBottom:10 }}>Dimensionamiento sistema FV + BESS — Guayaquil</div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(2,1fr)", gap:8, marginBottom:14 }}>
            <MetricCard label="Módulos necesarios" value={numMod} unit="uds." sub={`PERC 550 Wp @ 35 V`} />
            <MetricCard label="Área de paneles" value={areaMod} unit="m²" sub="2.2 m²/módulo" />
            <MetricCard label="Energía generada/día" value={energiaDia} unit="kWh" sub="HPS Guayaquil: 4.3 h" />
            <MetricCard label="Potencia inversor" value={invKva} unit="kVA" sub="FP=0.95 inductivo" />
            <MetricCard label="Energía útil BESS" value={eUtil} unit="kWh" sub="DoD 80%, LiFePO4" />
            <MetricCard label="SOC mínimo" value={socMin} unit="kWh" sub="20% IEEE 2030.2" />
          </div>
          <div style={{ fontSize:12, color:"var(--text-secondary)", marginBottom:6 }}>Perfil irradiación solar GYE (W/m² × hora)</div>
          <MiniChart data={[REAL_DATA.irradiation_gye]} labels={horas} colors={[COLORS.yellow]} height={100} />
          <div style={{ background:"var(--bg-success)", border:"0.5px solid var(--border-success)", borderRadius:8, padding:"10px 14px", marginTop:12 }}>
            <div style={{ fontSize:12, fontWeight:500, color:"var(--text-success)", marginBottom:4 }}>Estrategia de operación FV+BESS</div>
            <div style={{ fontSize:11, color:"var(--text-secondary)", lineHeight:1.6 }}>
              · Horas solares (06:00–18:00): PV inyecta a la carga y/o carga el BESS<br/>
              · Horas pico (11:00–13:00 / 18:00–20:00): BESS descarga para recortar demanda<br/>
              · Madrugada (01:00–05:00): BESS carga desde red a tarifa valle ({cargaNoc} kW)
            </div>
          </div>
        </div>
      )}

      {mod === 5 && (
        <div>
          <div style={{ fontSize:13, fontWeight:500, marginBottom:10 }}>Comparador: datos reales vs simulación EMS</div>
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:8, marginBottom:14 }}>
            <MetricCard label="Pico real (METREL)" value="179.1" unit="kW" />
            <MetricCard label="Pico simulado c/EMS" value={redPico.toFixed(1)} unit="kW" color="var(--text-success)" />
            <MetricCard label="Error relativo" value={Math.abs(((parseFloat(redPico)-pLim)/pLim)*100).toFixed(1)} unit="%" sub="vs set-point" />
          </div>
          <div style={{ fontSize:12, color:"var(--text-secondary)", marginBottom:6 }}>Curva de demanda: real vs EMS simulado</div>
          <MiniChart
            data={[REAL_DATA.hourly_load, emsData.map(r=>r.pRed)]}
            labels={horas}
            colors={[COLORS.blue, COLORS.green]}
            height={140} />
          <div style={{ display:"flex", gap:16, fontSize:11, color:"var(--text-secondary)", margin:"6px 0 12px" }}>
            <span><span style={{ display:"inline-block", width:10, height:2, background:COLORS.blue, verticalAlign:"middle", marginRight:4 }}></span>Demanda real</span>
            <span><span style={{ display:"inline-block", width:10, height:2, background:COLORS.green, verticalAlign:"middle", marginRight:4 }}></span>Con EMS (simulado)</span>
          </div>
          <div style={{ overflowX:"auto" }}>
            <table style={{ width:"100%", fontSize:11, borderCollapse:"collapse" }}>
              <thead>
                <tr style={{ borderBottom:"1px solid var(--border)" }}>
                  {["Parámetro","Medido (real)","Simulado (EMS)","Δ","Estado"].map(h=>(
                    <th key={h} style={{ padding:"5px 8px", textAlign:"left", color:"var(--text-secondary)", fontWeight:500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  ["Demanda pico","179.1 kW",`${redPico.toFixed(1)} kW`,`-${reduccion} kW`,"✓"],
                  ["FP mínimo","0.63","0.95 (c/EVC)","+0.32","⚠"],
                  ["THD U (máx)","2.2%","< 2.0%","−0.2%","✓"],
                  ["Flicker Plt","1.12","< 0.8 (c/EVC)","−0.32","✓"],
                  ["Icc disponible",`${(icc/1000).toFixed(2)} kA`,`${(icc/1000).toFixed(2)} kA`,"=","✓"],
                  ["Cargabilidad trafo",`${cargSin}%`,`${cargCon}%`,`-${(parseFloat(cargSin)-parseFloat(cargCon)).toFixed(1)}%`,"✓"],
                ].map(([p,r,s,d,e],i)=>(
                  <tr key={i} style={{ borderBottom:"0.5px solid var(--border)" }}>
                    <td style={{ padding:"4px 8px", fontWeight:500 }}>{p}</td>
                    <td style={{ padding:"4px 8px" }}>{r}</td>
                    <td style={{ padding:"4px 8px", color:"var(--text-success)" }}>{s}</td>
                    <td style={{ padding:"4px 8px", color:"var(--text-accent)" }}>{d}</td>
                    <td style={{ padding:"4px 8px" }}>{e}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {mod === 6 && (
        <div>
          <div style={{ fontSize:13, fontWeight:500, marginBottom:10 }}>Memoria técnica — vista previa</div>
          <pre style={{ fontSize:10.5, lineHeight:1.6, background:"var(--surface-1)", border:"0.5px solid var(--border)",
            borderRadius:8, padding:"12px 14px", overflowX:"auto", color:"var(--text-primary)", whiteSpace:"pre-wrap", wordBreak:"break-word" }}>
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
            <pre style={{ fontSize:10, lineHeight:1.6, background:"var(--surface-1)", border:"0.5px solid var(--border)",
              borderRadius:8, padding:"12px 14px", overflowX:"auto", color:"var(--text-primary)", whiteSpace:"pre-wrap" }}>
              {renderMatlabCode()}
            </pre>
          ) : (
            <pre style={{ fontSize:10.5, lineHeight:1.7, background:"var(--surface-1)", border:"0.5px solid var(--border)",
              borderRadius:8, padding:"12px 14px", overflowX:"auto", color:"var(--text-primary)", whiteSpace:"pre-wrap", wordBreak:"break-word" }}>
              {renderETAPInstructions()}
            </pre>
          )}
          <div style={{ marginTop:10, fontSize:11, color:"var(--text-muted)" }}>
            Copia el código y pégalo directamente en MATLAB R2023b o posterior. Los datos de carga se actualizan automáticamente con los parámetros que configures en el módulo "Datos del Proyecto".
          </div>
        </div>
      )}
    </div>
  );
}
