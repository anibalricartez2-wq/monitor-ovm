import streamlit as st
import requests
import re
import time
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia OPMET Pro", page_icon="✈️", layout="wide")

# Forzamos refresco cada 2 minutos para ser más agresivos
st_autorefresh(interval=120000, key="datarefresh")

API_KEY = "1c208dc6ec9442cd97575bdf518fb4a9"
AERODROMOS = "SAVV,SAVE,SAVT,SAVC,SAWC,SAWG,SAWE,SAWH"

# --- 2. FUNCIONES TÉCNICAS (CORREGIDAS) ---
def diff_angular(d1, d2):
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    if not texto or "No disponible" in texto: return None, None, None
    # Captura dirección, intensidad y ráfagas
    match = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', texto)
    if match:
        dir_v = int(match.group(1))
        vel = int(match.group(2))
        raf = int(match.group(3)[1:]) if match.group(3) else 0
        return dir_v, vel, raf
    return None, None, None

def auditar_criterios(reporte, taf):
    alertas = []
    dr, vr, rr = parse_viento(reporte)
    dt, vt, rt = parse_viento(taf)
    
    # CRITERIO VIENTO (Angular y Velocidad)
    if vr is not None and vt is not None:
        d_ang = diff_angular(dr, dt)
        if d_ang >= 60 and (vr >= 10 or vt >= 10):
            alertas.append(f"🚩 CRIT A: Giro de {d_ang}°")
        if abs(vr - vt) >= 10:
            alertas.append(f"🚩 CRIT B: Dif. Int. {abs(vr-vt)}kt")
        if rr >= (vt + 10):
            alertas.append(f"🚩 CRIT C: Ráfaga {rr}kt vs TAF")

    # CRITERIO VISIBILIDAD (Buscamos el número de 4 dígitos)
    vis_match = re.search(r'\s(\d{4})\s', reporte)
    if vis_match:
        vis = int(vis_match.group(1))
        for u in [5000, 3000, 1500, 800]:
            if vis < u:
                alertas.append(f"🚩 CRIT E: Vis < {u}m")
                break

    # CRITERIO TECHOS
    nubes = re.findall(r'(BKN|OVC)(\d{3})', reporte)
    if nubes:
        techo = min([int(n[1]) * 100 for n in nubes])
        for u in [1000, 500, 200]:
            if techo < u:
                alertas.append(f"🚩 CRIT I/J: Techo < {u}ft")
                break
                
    return alertas

# --- 3. INTERFAZ Y LLAMADA A API ---
st.title("🖥️ Auditoría OPMET - Patagonia")
st.write(f"Última lectura: **{datetime.now().strftime('%H:%M:%S')}**")

# Headers con desactivación de caché explícita
headers = {
    "X-API-Key": API_KEY,
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

try:
    # Generamos un ID único por cada segundo para que la API no nos devuelva datos viejos
    timestamp = int(time.time())
    
    # Peticiones con el parámetro 'nocache'
    r_m = requests.get(f"https://api.checkwx.com/metar/{AERODROMOS}/decoded?cache={timestamp}", headers=headers)
    r_t = requests.get(f"https://api.checkwx.com/taf/{AERODROMOS}/decoded?cache={timestamp}", headers=headers)
    r_s = requests.get(f"https://api.checkwx.com/speci/{AERODROMOS}/decoded?cache={timestamp}", headers=headers)
    
    if r_m.status_code == 200:
        data_m = r_m.json().get("data", [])
        data_t = r_t.json().get("data", [])
        data_s = r_s.json().get("data", [])

        # Diccionarios para cruzar datos por OACI
        # Extraemos el raw del METAR/TAF/SPECI
        metars = {m['icao']: m['raw_text'] for m in data_m if 'icao' in m}
        tafs = {t['icao']: t['raw_text'] for t in data_t if 'icao' in t}
        specis = {s['icao']: s['raw_text'] for s in data_s if 'icao' in s}
        
        cols = st.columns(2)
        # Usamos el orden de tu lista de aeródromos
        for i, icao in enumerate(AERODROMOS.split(',')):
            metar = metars.get(icao, "No disponible")
            taf = tafs.get(icao, "No disponible")
            speci = specis.get(icao, None)
            
            # Decidimos qué reporte vigilar (SPECI tiene prioridad)
            reporte_actual = speci if speci else metar
            alertas = auditar_criterios(reporte_actual, taf) if taf != "No disponible" and reporte_actual != "No disponible" else []
            
            with cols[i % 2]:
                estado = "⚠️ ALERTA" if alertas else "✅ OK"
                with st.expander(f"📍 {icao} - {estado}", expanded=True):
                    st.caption("TAF:")
                    st.code(taf, language="bash")
                    
                    if speci:
                        st.warning(f"🔔 SPECI ACTIVO:\n`{speci}`")
                    
                    st.markdown(f"**METAR:** `{metar}`")
                    
                    if alertas:
                        for a in alertas: st.error(a)
                    elif "No disponible" not in reporte_actual:
                        st.success("Vigilancia normal.")
    else:
        st.error(f"Error de API: Código {r_m.status_code}")

except Exception as e:
    st.error(f"Error en el proceso: {e}")