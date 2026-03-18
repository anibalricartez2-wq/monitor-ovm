import streamlit as st
import requests
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Auditoría OPMET Pro + SPECI",
    page_icon="✈️",
    layout="wide"
)

# --- 2. AUTO-REFRESCO (Cada 5 minutos) ---
st_autorefresh(interval=300000, key="datarefresh")

# --- 3. CONFIGURACIÓN ---
API_KEY = "1c208dc6ec9442cd97575bdf518fb4a9"
AERODROMOS = "SAVV,SAVE,SAVT,SAVC,SAWC,SAWG,SAWE,SAWH"

# --- 4. FUNCIONES TÉCNICAS (Regex) ---
def parse_viento(texto):
    if not texto or texto == "No disponible": return None, None, None
    match = re.search(r'(\d{3})(\d{2})(G\d{2})?KT', texto)
    if match:
        return int(match.group(1)), int(match.group(2)), (int(match.group(3)[1:]) if match.group(3) else 0)
    return None, None, None

def parse_visibilidad(texto):
    if not texto: return 9999
    if "CAVOK" in texto: return 9999
    match = re.search(r'\s(\d{4})\s', texto)
    return int(match.group(1)) if match else 9999

def parse_nubes(texto):
    if not texto: return 10000
    matches = re.findall(r'(BKN|OVC)(\d{3})', texto)
    if matches:
        return min([int(m[1]) * 100 for m in matches])
    return 10000

def auditar_criterios(reporte, taf):
    """Compara un reporte (METAR o SPECI) contra el TAF."""
    alertas = []
    dr, vr, rr = parse_viento(reporte)
    dt, vt, rt = parse_viento(taf)
    visr = parse_visibilidad(reporte)
    techo = parse_nubes(reporte)

    if vr is not None and vt is not None:
        if abs(dr - dt) >= 60 and (vr >= 10 or vt >= 10):
            alertas.append(f"🚩 CRIT A: Cambio Dir. {abs(dr-dt)}°")
        if abs(vr - vt) >= 10:
            alertas.append(f"🚩 CRIT B: Dif. Intensidad {abs(vr-vt)}kt")
        if rr >= (vt + 10):
            alertas.append(f"🚩 CRIT C: Ráfaga {rr}kt detectada")
    
    for u in [5000, 3000, 1500, 800]:
        if visr < u:
            alertas.append(f"🚩 CRIT E: Visibilidad < {u}m")
            break
            
    for u in [1000, 500, 200]:
        if techo < u:
            alertas.append(f"🚩 CRIT I/J: Techo bajo {techo}ft")
            break
    return alertas

# --- 5. INTERFAZ ---
st.title("🖥️ Auditoría OPMET - Vigilancia METAR/SPECI")
st.write(f"Última actualización: **{datetime.now().strftime('%H:%M:%S')}**")

headers = {"X-API-Key": API_KEY}

try:
    # Pedimos METAR, TAF y ahora también SPECI
    r_m = requests.get(f"https://api.checkwx.com/metar/{AERODROMOS}", headers=headers)
    r_t = requests.get(f"https://api.checkwx.com/taf/{AERODROMOS}", headers=headers)
    r_s = requests.get(f"https://api.checkwx.com/speci/{AERODROMOS}", headers=headers)
    
    if r_m.status_code == 200:
        metars = r_m.json().get("data", [])
        tafs = {t[4:8] if 'TAF' in t else t[:4]: t for t in r_t.json().get("data", [])}
        specis = {s[6:10] if 'SPECI' in s else s[:4]: s for s in r_s.json().get("data", [])}
        
        cols = st.columns(2)
        for i, metar in enumerate(metars):
            icao = next((icao for icao in AERODROMOS.split(',') if icao in metar), "UNKN")
            taf = tafs.get(icao, "No disponible")
            speci = specis.get(icao, None)
            
            # La auditoría prioriza el SPECI si existe, sino usa el METAR
            reporte_vigilancia = speci if speci else metar
            alertas = auditar_criterios(reporte_vigilancia, taf) if taf != "No disponible" else []
            
            with cols[i % 2]:
                estado = "⚠️ ALERTA" if alertas else "✅ OK"
                with st.expander(f"📍 {icao} - {estado}", expanded=True):
                    # Visualización del TAF
                    st.caption("TAF VIGENTE:")
                    st.code(taf, language="bash")

                    # Visualización del SPECI (Si existe)
                    if speci:
                        st.warning(f"🔔 SPECI DETECTADO:\n`{speci}`")
                    
                    # Visualización del METAR
                    st.markdown(f"**METAR:** `{metar}`")

                    # Mostrar alertas
                    if alertas:
                        for a in alertas: st.error(a)
                    elif taf != "No disponible":
                        st.success("Vigilancia normal.")

except Exception as e:
    st.error(f"Error: {e}")