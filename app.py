import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA Y TEMA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# Barra lateral para el Menú de Selección de Pantalla
with st.sidebar:
    st.header("⚙️ Configuración")
    tema = st.selectbox(
        "Modo de Pantalla:",
        ["Sistema", "Día", "Noche"],
        index=0
    )

# Aplicar el tema visualmente
if tema == "Día":
    st.markdown("<style>reportview-container { background: white; color: black; }</style>", unsafe_allow_html=True)
elif tema == "Noche":
    st.markdown("<style>stApp { background-color: #0E1117; color: white; }</style>", unsafe_allow_html=True)

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
st.title("🖥️ Monitor de Vigilancia e Historial - FIR SAVC")
ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
st.write(f"Sincronizado: **{ahora}**")

# Llamada a los datos
datos_raw = obtener_datos_checkwx(AERODROMOS)

# Procesamiento y guardado en trazabilidad
reportes_actuales = {icao: "Sin datos" for icao in AERODROMOS}
nuevos_registros = []

for metar in datos_raw:
    for icao in AERODROMOS:
        if icao in metar:
            reportes_actuales[icao] = metar
            estado = "RAFAGAS" if "G" in metar else "NORMAL"
            # Añadir al historial de sesión
            nuevos_registros.append({
                "Fecha_Hora": ahora,
                "OACI": icao,
                "METAR": metar,
                "Estado": estado
            })

# Actualizar el historial en la sesión del navegador
if nuevos_registros:
    df_nuevos = pd.DataFrame(nuevos_registros)
    st.session_state.historial = pd.concat([st.session_state.historial, df_nuevos], ignore_index=True)

# Renderizado de Tarjetas
cols = st.columns(2)
for i, icao in enumerate(AERODROMOS):
    metar_txt = reportes_actuales[icao]
    with cols[i % 2]:
        status_label = "⚠️" if "G" in metar_txt else "✅"
        with st.expander(f"{status_label} {icao}", expanded=True):
            st.code(metar_txt)

st.divider()

# --- 5. EXPORTAR A EXCEL (CSV) ---
st.subheader("📋 Trazabilidad de la Guardia")
if not st.session_state.historial.empty:
    st.dataframe(st.session_state.historial.tail(10), use_container_width=True)
    
    # Convertir a CSV para descarga
    csv = st.session_state.historial.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Historial Completo (Excel/CSV)",
        data=csv,
        file_name=f"trazabilidad_metar_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
else:
    st.info("El historial comenzará a grabarse a las 21:00 hs cuando la API se reactive.")
