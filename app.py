import streamlit as st
import requests
import re
import random
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# Inicializar el historial en la memoria de la sesión
if 'historial_alertas' not in st.session_state:
    st.session_state.historial_alertas = []

hide_st_style = """
            <style>
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            .st-emotion-cache-1wbqy5l {display:none;}
            .block-container {padding-top: 2rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st_autorefresh(interval=120000, key="datarefresh")

API_KEY = "1c208dc6ec9442cd97575bdf518fb4a9"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# --- 2. FUNCIONES TÉCNICAS ---
def diff_angular(d1, d2):
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    if not texto or "Sin datos" in texto: return None, None, None
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
                # Guardar en historial
                st.session_state.historial_alertas.append({"Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "OACI": icao, "Tipo": "Giro Viento", "Detalle": msg})
        
        if abs(vr - vt) >= 10:
            msg = f"CRIT B: Dif Int {abs(vr-vt)}kt"
            alertas.append(msg)
            st.session_state.historial_alertas.append({"Fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "OACI": icao, "Tipo": "Intensidad", "Detalle": msg})

    return alertas

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia FIR SAVC")

# SECCIÓN DE RESPALDO (Sidebar o Arriba)
with st.sidebar:
    st.header("📊 Respaldo de Desvíos")
    if st.session_state.historial_alertas:
        df_log = pd.DataFrame(st.session_state.historial_alertas)
        st.dataframe(df_log.tail(10)) # Muestra los últimos 10
        
        # Botón para descargar el Excel/CSV
        csv = df_log.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar Registro de Desvíos",
            data=csv,
            file_name=f"log_vigilancia_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv',
        )
        if st.button("Limpiar Historial"):
            st.session_state.historial_alertas = []
            st.rerun()
    else:
        st.write("No hay desvíos registrados en esta sesión.")

st.write(f"Última actualización: **{datetime.now().strftime('%H:%M:%S')}**")

cols = st.columns(2)
headers = {"X-API-Key": API_KEY}

for i, icao in enumerate(AERODROMOS):
    try:
        r_hash = random.randint(1, 999999)
        res_m = requests.get(f"https://api.checkwx.com/metar/{icao}?cache={r_hash}", headers=headers).json()
        metar = res_m.get('data', ['Sin datos'])[0]
        res_t = requests.get(f"https://api.checkwx.com/taf/{icao}?cache={r_hash}", headers=headers).json()
        taf = res_t.get('data', ['Sin datos'])[0]
        
        alertas = auditar(icao, metar, taf) if "Sin datos" not in [metar, taf] else []

        with cols[i % 2]:
            estado_label = "⚠️ ALERTA" if alertas else "✅ OK"
            with st.expander(f"📍 {icao} - {estado_label}", expanded=True):
                st.caption("TAF:")
                st.code(taf)
                st.markdown(f"**ACTUAL:** `{metar}`")
                for a in alertas: st.error(a)
    except Exception:
        st.error(f"Reconectando {icao}...")