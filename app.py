import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# ELIMINACIÓN TOTAL DE MENÚS Y "VIEW SOURCE"
st.markdown("""
    <style>
    /* Oculta el menú de hamburguesa (tres líneas) */
    #MainMenu {visibility: hidden;}
    /* Oculta el footer de Streamlit */
    footer {visibility: hidden;}
    /* Oculta el botón de Deploy y el de Ver Código en la parte superior */
    .stDeployButton {display:none;}
    header {visibility: hidden;}
    /* Oculta los botones de 'View Source' que aparecen en el menú de la derecha */
    button[title="View source"] {display: none;}
    /* Ajuste para que el contenido no quede pegado al techo */
    .block-container {padding-top: 2rem;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (PANEL DE CONTROL) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    tema = st.selectbox(
        "Modo de Pantalla:",
        ["Día", "Noche", "Sistema"],
        index=2
    )
    st.divider()
    st.info("Actualización automática: cada 15 min.")

# --- 3. CONFIGURACIÓN TÉCNICA ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Refresco cada 15 minutos (900.000 ms)
st_autorefresh(interval=900000, key="vigilancia_refresh")

# Historial de Sesión
if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Fecha_Hora", "OACI", "METAR", "Estado"])

# --- 4. MOTOR DE DATOS ---
def obtener_datos_checkwx(icao_list):
    icaos = ",".join(icao_list)
    url = f"https://api.checkwx.com/metar/{icaos}"
    headers = {"X-API-Key": API_KEY}
    try:
        res = requests.get(url, headers=headers, timeout=15).json()
        return res.get('data', [])
    except:
        return []

# --- 5. INTERFAZ PRINCIPAL ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
ahora = datetime.now().strftime('%H:%M:%S')
st.write(f"Sincronizado: **{ahora}**")

# Datos
datos_raw = obtener_datos_checkwx(AERODROMOS)

# Procesar y guardar en historial
reportes = {icao: "Esperando reinicio (21:00 hs)..." for icao in AERODROMOS}
nuevos_logs = []

for metar in datos_raw:
    for icao in AERODROMOS:
        if icao in metar:
            reportes[icao] = metar
            estado = "RAFAGAS" if "G" in metar else "NORMAL"
            nuevos_logs.append({
                "Fecha_Hora": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "OACI": icao,
                "METAR": metar,
                "Estado": estado
            })

if nuevos_logs:
    st.session_state.historial = pd.concat([st.session_state.historial, pd.DataFrame(nuevos_logs)], ignore_index=True)

# Tarjetas
cols = st.columns(2)
for i, icao in enumerate(AERODROMOS):
    metar_txt = reportes[icao]
    with cols[i % 2]:
        status_icon = "⚠️" if "G" in metar_txt else "✅"
        with st.expander(f"{status_icon} {icao}", expanded=True):
            st.code(metar_txt)

st.divider()

# --- 6. TRAZABILIDAD ---
st.subheader("📊 Historial para Excel")
if not st.session_state.historial.empty:
    st.dataframe(st.session_state.historial.tail(10), use_container_width=True)
    csv = st.session_state.historial.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar CSV",
        data=csv,
        file_name=f"trazabilidad_{datetime.now().strftime('%d-%m-%Y')}.csv",
        mime="text/csv",
    )
else:
    st.info("El registro comenzará a las 21:00 hs.")
