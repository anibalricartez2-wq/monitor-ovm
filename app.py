import streamlit as st
import requests
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# Usamos tu clave que ya sabemos que funciona
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Refresco cada 20 minutos para cuidar los créditos de la API (Suficiente para Vigilancia)
st_autorefresh(interval=1200000, key="vigilancia_refresh")

# --- 2. MOTOR DE DATOS (OPTIMIZADO) ---
def obtener_datos_checkwx(icao_list):
    """Consulta todos los aeródromos en un solo pedido para ahorrar créditos."""
    icaos = ",".join(icao_list)
    url = f"https://api.checkwx.com/metar/{icaos}/decoded"
    headers = {"X-API-Key": API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        return res.get('data', [])
    except:
        return []

# --- 3. INTERFAZ ---
st.title("🖥️ Monitor Automático FIR SAVC")
st.write(f"Actualizado: **{datetime.now().strftime('%H:%M:%S')}**")

if st.button("🔄 Forzar Actualización"):
    st.rerun()

datos = obtener_datos_checkwx(AERODROMOS
