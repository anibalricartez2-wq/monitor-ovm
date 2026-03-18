import streamlit as st
import requests
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Auditoría OPMET Integral", page_icon="✈️", layout="wide")

# Autorefresco cada 5 minutos
st_autorefresh(interval=300000, key="datarefresh")

API_KEY = "1c208dc6ec9442cd97575bdf518fb4a9"
AERODROMOS = "SAVV,SAVE,SAVT,SAVC,SAWC,SAWG,SAWE,SAWH"

# --- FUNCIONES TÉCNICAS (Basadas en normativa SMN) ---
def parse_viento(texto):
    match = re.search(r'(\d{3})(\d{2})(G\d{2})?KT', texto)
    if match:
        return int(match.group(1)), int(match.group(2)), (int(match.group(3)[1:]) if match.group(3) else 0)
    return None, None, None

def parse_visibilidad(texto):
    if "CAVOK" in texto: return 9999
    match = re.search(r'\s(\d{4})\s', texto)
    return int(match.group(1)) if match else 9999

def parse_nubes(texto):
    matches = re.findall(r'(BKN|OVC)(\d{3})', texto)
    if matches:
        return min([int(m[1]) * 100 for m in matches])
    return 10000

def auditar_criterios(metar, taf):
    alertas = []
    dm, vm, rm = parse_viento(metar)
    dt, vt, rt = parse_viento(taf)
    vism = parse_visibilidad(metar)
    techo = parse_nubes(metar)

    if vm is not None and vt is not None:
        # Criterio A: Cambio de dirección >= 60° (Vto > 10kt)
        if abs(dm - dt) >= 60 and (vm >= 10 or vt >= 10):
            alertas.append(f"🚩 CRIT A: Cambio Dir. {abs(dm-dt)}° (MTR:{dm}° / TAF:{dt}°)")
        # Criterio B: Cambio de intensidad >= 10kt
        if abs(vm - vt) >= 10:
            alertas.append(f"🚩 CRIT B: Dif. Intensidad {abs(vm-vt)}kt (MTR:{vm} / TAF:{vt})")
        # Criterio C: Ráfagas
        if rm >= (vt + 10):
            alertas.append(f"🚩 CRIT C: Ráfaga {rm}kt supera en 10+ al TAF ({vt}kt)")
    
    # Criterio E: Visibilidad (Umbrales críticos)
    for u in [5000, 3000, 1500, 800]:
        if vism < u:
            alertas.append(f"🚩 CRIT E: Visibilidad < {u}m (Actual: {vism}m)")
            break
            
    # Criterio I/J: Techo de nubes
    for u in [1000, 500, 200]:
        if techo < u:
            alertas.append(f"🚩 CRIT I/J: Techo bajo {techo}ft")
            break
    return alertas

# --- INTERFAZ WEB ---
st.title("🖥️ Auditoría de Vigilancia OPMET - Patagonia")
st.write(f"Actualización automática: **{datetime.now().strftime('%H:%M:%S')}**")

headers = {"X-API-Key": API_KEY}

try:
    r_m = requests.get(f"https://api.checkwx.com/metar/{AERODROMOS}", headers=headers)
    r_t = requests.get(f"https://api.checkwx.com/taf/{AERODROMOS}", headers=headers)
    
    if r_m.status_code == 200:
        # Diccionario de TAFs
        datos_taf = r_t.json().get("data", [])
        tafs_dict = {t[4:8] if 'TAF' in t else t[:4]: t for t in datos_taf}
        
        cols = st.columns(2)
        for i, metar in enumerate(r_m.json().get("data", [])):
            icao = next((icao for icao in AERODROMOS.split(',') if icao in metar), "UNKN")
            taf = tafs_dict.get(icao, "No disponible")
            alertas = auditar_criterios(metar, taf) if taf != "No disponible" else []
            
            with cols[i % 2]:
                with st.expander(f"📍 {icao} {'⚠️ ALERTA' if alertas else '✅ OK'}", expanded=True):
                    # Sección METAR
                    st.markdown("**METAR Actual:**")
                    st.info(f"`{metar}`")
                    
                    # Sección TAF (Novedad)
                    st.markdown("**TAF Vigente:**")
                    if taf != "No disponible":
                        st.code(taf, language="bash")
                    else:
                        st.warning("⚠️ No se encontró TAF para este aeródromo.")

                    # Sección de Alertas
                    if alertas:
                        for a in alertas:
                            st.error(a)
                    elif taf != "No disponible":
                        st.success("Vigilancia normal: METAR coincide con TAF.")
    else:
        st.error("Error al obtener datos de la API.")
except Exception as e:
    st.error(f"Error de conexión: {e}")

st.sidebar.button("🔄 Actualizar Manual")