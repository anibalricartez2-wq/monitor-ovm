import streamlit as st
import requests
import re
import random
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# NUEVA API KEY (Generada ahora)
API_KEY = "34f1989668804533a39396f47702ecbc" 
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

if 'historial_alertas' not in st.session_state:
    st.session_state.historial_alertas = []

hide_st_style = """
            <style>
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            .st-emotion-cache-1wbqy5l {display:none;}
            .block-container {padding-top: 1.5rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Refresco cada 15 min (900.000 ms)
st_autorefresh(interval=900000, key="datarefresh")

# --- 2. LÓGICA TÉCNICA ---
def diff_angular(d1, d2):
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    if not texto or "Sin datos" in texto: return None, None, None
    if "00000KT" in texto: return 0, 0, 0
    match = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', texto)
    if match:
        return int(match.group(1)), int(match.group(2)), (int(match.group(3)[1:]) if match.group(3) else 0)
    return None, None, None

def auditar(icao, reporte, taf):
    alertas = []
    dr, vr, rr = parse_viento(reporte)
    dt, vt, rt = parse_viento(taf)
    if vr is not None and vt is not None:
        if vr >= 10 or vt >= 10:
            d_ang = diff_angular(dr, dt)
            if d_ang >= 60:
                msg = f"CRIT A: Giro {d_ang}°"
                alertas.append(msg)
                st.session_state.historial_alertas.append({"H_Local": datetime.now().strftime("%H:%M:%S"), "OACI": icao, "Alerta": "GIRO VTO", "Valor": f"{d_ang}°"})
        if abs(vr - vt) >= 10:
            msg = f"CRIT B: Dif Int {abs(vr-vt)}kt"
            alertas.append(msg)
            st.session_state.historial_alertas.append({"H_Local": datetime.now().strftime("%H:%M:%S"), "OACI": icao, "Alerta": "INTENSIDAD", "Valor": f"{abs(vr-vt)}kt"})
    return alertas

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia FIR SAVC")

if st.session_state.historial_alertas:
    with st.expander("📊 Registro de Desvíos", expanded=False):
        df_log = pd.DataFrame(st.session_state.historial_alertas)
        st.table(df_log.tail(5))
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button("📥 DESCARGAR LOG", csv, f"vigilancia_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")

st.write(f"Sincronizado (15m): **{datetime.now().strftime('%H:%M:%S')}**")

# Botón manual de emergencia
if st.button("🔄 Forzar Actualización"):
    st.rerun()

cols = st.columns(2)
headers = {"X-API-Key": API_KEY}

for i, icao in enumerate(AERODROMOS):
    try:
        # Agregamos un número aleatorio al final de la URL para que no use datos viejos
        url_m = f"https://api.checkwx.com/metar/{icao}?decoded=false&nocache={random.randint(1,9999)}"
        url_t = f"https://api.checkwx.com/taf/{icao}?decoded=false&nocache={random.randint(1,9999)}"
        
        res_m = requests.get(url_m, headers=headers, timeout=10).json()
        metar = res_m.get('data', ['Sin datos'])[0]
        
        res_t = requests.get(url_t, headers=headers, timeout=10).json()
        taf = res_t.get('data', ['Sin datos'])[0]
        
        alertas = auditar(icao, metar, taf) if "Sin datos" not in [metar, taf] else []

        with cols[i % 2]:
            estado = "⚠️ ALERTA" if alertas else "✅ OK"
            with st.expander(f"📍 {icao} - {estado}", expanded=True):
                st.caption("TAF:")
                st.code(taf)
                st.markdown(f"**ACTUAL:** `{metar}`")
                for a in alertas: st.error(a)
    except Exception as e:
        with cols[i % 2]:
            st.warning(f"📍 {icao}: Sin respuesta del servidor.")