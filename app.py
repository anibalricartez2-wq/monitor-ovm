import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# OCULTAR MENÚ DE STREAMLIT Y OPCIÓN "VIEW SOURCE"
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stDeployButton {display:none;}
            [data-testid="stHeader"] {display: none;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# Barra lateral para el Menú de Selección de Pantalla
with st.sidebar:
    st.header("⚙️ Configuración")
    tema = st.selectbox(
        "Modo de Pantalla:",
        ["Sistema", "Día", "Noche"],
        index=0
    )

# API KEY y Configuración
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Refresco cada 15 minutos (96 consultas/día)
st_autorefresh(interval=900000, key="vigilancia_refresh")

# --- 2. GESTIÓN DE TRAZABILIDAD (HISTORIAL) ---
if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Fecha_Hora", "OACI", "METAR", "Estado"])

# --- 3. MOTOR DE DATOS ---
def obtener_datos_checkwx(icao_list):
    icaos = ",".join(icao_list)
    url = f"https://api.checkwx.com/metar/{icaos}"
    headers = {"X-API-Key": API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        return res.get('data', [])
    except:
        return []

# --- 4. INTERFAZ ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
ahora = datetime.now().strftime('%H:%M:%S')
st.write(f"Última sincronización automática: **{ahora}**")

# Llamada a los datos
datos_raw = obtener_datos_checkwx(AERODROMOS)

# Procesamiento
reportes_actuales = {icao: "Esperando reinicio de API (21:00 hs)..." for icao in AERODROMOS}
nuevos_registros = []

for metar in datos_raw:
    for icao in AERODROMOS:
        if icao in metar:
            reportes_actuales[icao] = metar
            estado = "RAFAGAS" if "G" in metar else "NORMAL"
            nuevos_registros.append({
                "Fecha_Hora": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "OACI": icao,
                "METAR": metar,
                "Estado": estado
            })

# Actualizar el historial
if nuevos_registros:
    df_nuevos = pd.DataFrame(nuevos_registros)
    st.session_state.historial = pd.concat([st.session_state.historial, df_nuevos], ignore_index=True)

# Tarjetas de Aeródromos
cols = st.columns(2)
for i, icao in enumerate(AERODROMOS):
    metar_txt = reportes_actuales[icao]
    with cols[i % 2]:
        status_color = "red" if "G" in metar_txt else "green"
        with st.expander(f"📍 {icao}", expanded=True):
            st.code(metar_txt)
            if "G" in metar_txt:
                st.warning("⚠️ Viento fuerte detectado")

st.divider()

# --- 5. SECCIÓN DE TRAZABILIDAD Y EXCEL ---
st.subheader("📊 Historial de la Guardia (Trazabilidad)")
if not st.session_state.historial.empty:
    st.dataframe(st.session_state.historial.tail(10), use_container_width=True)
    
    csv = st.session_state.historial.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Reporte para Excel (.csv)",
        data=csv,
        file_name=f"log_metar_{datetime.now().strftime('%d-%m-%Y')}.csv",
        mime="text/csv",
    )
else:
    st.info("El registro comenzará automáticamente a las 21:00 hs.")
