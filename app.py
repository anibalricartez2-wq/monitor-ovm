import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

hide_st_style = """<style>.stDeployButton {display:none;} footer {visibility: hidden;} .block-container {padding-top: 1.5rem;}</style>"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# Refresco cada 10 min
st_autorefresh(interval=600000, key="datarefresh")

# --- 2. LÓGICA DE EXTRACCIÓN (SCRAPING DE TABLA SMN) ---
def get_smn_table():
    """Intenta leer la tabla de la web de 'Estado del Tiempo' del SMN."""
    url = "https://www.smn.gob.ar/estado-del-tiempo"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        # Buscamos las tablas en la página de inicio del SMN
        dfs = pd.read_html(url, header=0)
        if dfs:
            return dfs[0] # Retorna la primera tabla (la de METARs)
    except Exception as e:
        return f"ERROR: {str(e)}"
    return None

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia FIR SAVC (Escaneo Visual SMN)")
st.write(f"Sincronizado: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Forzar Escaneo"):
    st.rerun()

st.divider()

# Intentamos obtener la tabla completa
tabla_smn = get_smn_table()

cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    reporte = "No encontrado en tabla"
    
    # Buscamos el OACI en la tabla de Pandas
    if isinstance(tabla_smn, pd.DataFrame):
        # El SMN a veces usa nombres de ciudades, buscamos coincidencia
        resultado = tabla_smn[tabla_smn.astype(str).apply(lambda x: x.str.contains(icao, case=False)).any(axis=1)]
        if not resultado.empty:
            # Si lo encuentra, armamos un string con los datos de las columnas
            row = resultado.iloc[0]
            reporte = f"{icao} | Temp: {row.get('Temp. (°C)', '-')} | Vto: {row.get('Viento', '-')} | Vis: {row.get('Visibilidad (km)', '-')}"

    with cols[i % 2]:
        with st.expander(f"📍 {icao}", expanded=True):
            if "ERROR" in str(tabla_smn):
                st.error("❌ Error de acceso a la web del SMN.")
            elif reporte == "No encontrado en tabla":
                st.info(f"⚪ {icao}: Estación no presente en la tabla actual.")
            else:
                st.success(f"✅ {reporte}")

# PANEL DE CONTROL PARA ACOSTA
with st.expander("📊 Ver Tabla Completa del SMN"):
    if isinstance(tabla_smn, pd.DataFrame):
        st.dataframe(tabla_smn)
    else:
        st.write("No se pudo cargar la tabla comparativa.")
