import streamlit as st
import requests
import re
import random
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia OPMET Patagonia", page_icon="✈️", layout="wide")

# OCULTAR SOLO LO ADMINISTRATIVO (Mantiene el menú de visualización)
hide_st_style = """
            <style>
            /* Oculta el botón de Deploy/Manage que ves vos como dueño */
            .stDeployButton {display:none;}
            /* Oculta el footer de Streamlit */
            footer {visibility: hidden;}
            /* Oculta el icono de la computadora (viewer/editor) */
            .st-emotion-cache-1wbqy5l {display:none;}
            /* Ajusta el margen superior para que se vea más limpio */
            .block-container {padding-top: 2rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Refresco cada 2 minutos
st_autorefresh(interval=120000, key="datarefresh")

API_KEY = "1c208dc6ec9442cd97575bdf518fb4a9"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

def diff_angular(d1, d2):
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    if not texto or "Sin datos" in texto: return None, None, None
    match = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', texto)
    if match:
        return int(match.group(1)), int(match.group(2)), (int(match.group(3)[1:]) if match.group(3) else 0)
    return None, None, None

def auditar(reporte, taf):
    alertas = []
    dr, vr, rr = parse_viento(reporte)
    dt, vt, rt = parse_viento(taf)
    if vr is not None and vt is not None:
        if vr >= 10 or vt >= 10:
            d_ang = diff_angular(dr, dt)
            if d_ang >= 60:
                alertas.append(f"🚩 CRIT A: Giro de {d_ang}° (Intensidad >= 10kt)")
        if abs(vr - vt) >= 10:
            alertas.append(f"🚩 CRIT B: Dif. Int. {abs(vr-vt)}kt")
        if rr >= (vt + 10):
            alertas.append(f"🚩 CRIT C: Ráfaga de {rr}kt detectada")
    return alertas

# --- 2. INTERFAZ ---
st.title("🖥️ Monitor de Despacho OPMET")
st.write(f"Última lectura: **{datetime.now().strftime('%H:%M:%S')}**")

cols = st.columns(2)
headers = {"X-API-Key": API_KEY}

for i, icao in enumerate(AERODROMOS):
    try:
        r_hash = random.randint(1, 999999)
        res_m = requests.get(f"https://api.checkwx.com/metar/{icao}?cache={r_hash}", headers=headers).json()
        metar = res_m.get('data', ['Sin datos'])[0]
        res_t = requests.get(f"https://api.checkwx.com/taf/{icao}?cache={r_hash}", headers=headers).json()
        taf = res_t.get('data', ['Sin datos'])[0]
        alertas = auditar(metar, taf) if "Sin datos" not in [metar, taf] else []

        with cols[i % 2]:
            estado_label = "⚠️ ALERTA" if alertas else "✅ OK"
            with st.expander(f"📍 {icao} - {estado_label}", expanded=True):
                st.caption("TAF VIGENTE:")
                st.code(taf, language="bash")
                if "SPECI" in metar:
                    st.warning(f"🔔 SPECI: `{metar}`")
                else:
                    st.markdown(f"**ACTUAL:** `{metar}`")
                if alertas:
                    for a in alertas: st.error(a)
                elif "Sin datos" not in metar:
                    st.success("Operación normal.")
    except Exception:
        with cols[i % 2]:
            st.error(f"Error en {icao}: Reconectando...")