import streamlit as st
import requests
import re
import random
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia OPMET Patagonia", page_icon="✈️", layout="wide")

# Refresco cada 2 minutos
st_autorefresh(interval=120000, key="datarefresh")

API_KEY = "1c208dc6ec9442cd97575bdf518fb4a9"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

def diff_angular(d1, d2):
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    if not texto or "No disponible" in texto: return None, None, None
    match = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', texto)
    if match:
        return int(match.group(1)), int(match.group(2)), (int(match.group(3)[1:]) if match.group(3) else 0)
    return None, None, None

def auditar(reporte, taf):
    alertas = []
    dr, vr, rr = parse_viento(reporte)
    dt, vt, rt = parse_viento(taf)
    if vr is not None and vt is not None:
        d_ang = diff_angular(dr, dt)
        if d_ang >= 60 and (vr >= 10 or vt >= 10): alertas.append(f"🚩 CRIT A: Giro {d_ang}°")
        if abs(vr - vt) >= 10: alertas.append(f"🚩 CRIT B: Dif Int {abs(vr-vt)}kt")
        if rr >= (vt + 10): alertas.append(f"🚩 CRIT C: Ráfaga {rr}kt")
    return alertas

st.title("🖥️ Monitor de Despacho OPMET")
st.write(f"Última actualización: **{datetime.now().strftime('%H:%M:%S')}**")

cols = st.columns(2)
headers = {"X-API-Key": API_KEY}

for i, icao in enumerate(AERODROMOS):
    try:
        # TRUCO ANTI-CACHE: Agregamos un número aleatorio al final para forzar datos nuevos
        r_hash = random.randint(1, 999999)
        
        # Pedimos el METAR
        url_m = f"https://api.checkwx.com/metar/{icao}?cache={r_hash}"
        res_m = requests.get(url_m, headers=headers).json()
        metar = res_m.get('data', ['Sin datos'])[0]
        
        # Pedimos el TAF
        url_t = f"https://api.checkwx.com/taf/{icao}?cache={r_hash}"
        res_t = requests.get(url_t, headers=headers).json()
        taf = res_t.get('data', ['Sin datos'])[0]

        alertas = auditar(metar, taf) if "Sin datos" not in [metar, taf] else []

        with cols[i % 2]:
            with st.expander(f"📍 {icao} - {'⚠️ ALERTA' if alertas else '✅ OK'}", expanded=True):
                st.caption("TAF:")
                st.code(taf)
                st.markdown(f"**ACTUAL:** `{metar}`")
                for a in alertas: st.error(a)
                if not alertas and "Sin datos" not in metar:
                    st.success("Sin discrepancias.")
    except Exception as e:
        with cols[i % 2]:
            st.error(f"Error en {icao}: Reconectando...")