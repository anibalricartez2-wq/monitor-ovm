import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# BLOQUEO AGRESIVO DE MENÚS DE CÓDIGO
st.markdown("""
    <style>
    /* 1. Ocultar el menú de hamburguesa (derecha) y footer */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    
    /* 2. Ocultar específicamente los botones de Ver Código/GitHub en el Header */
    header [data-testid="stHeaderActionElements"] {
        display: none !important;
    }
    
    /* 3. Asegurar que la flecha de la Sidebar (izquierda) SÍ sea visible */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
    }

    /* 4. Limpieza estética del fondo del header */
    header {
        background-color: rgba(0,0,0,0) !important;
        color: rgba(0,0,0,0) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (MENU DE PANTALLA) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    tema = st.selectbox(
        "Modo de Pantalla:",
        ["Día", "Noche", "Sistema"],
        index=2
    )
    st.divider()
    st.info("Actualización automática cada 15 min.")

# --- 3. CONFIGURACIÓN TÉCNICA ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Refresco cada 15 min (900.000 ms)
st_autorefresh(interval=900000, key="vigilancia_refresh")

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

# Llamada a la API
datos_raw = obtener_datos_checkwx(AERODROMOS)

# Procesamiento de reportes
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
st.subheader("📊 Historial de Trazabilidad")
if not st.session_state.historial.empty:
    st.dataframe(st.session_state.historial.tail(10), use_container_width=True)
    csv = st.session_state.historial.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Historial (.csv)",
        data=csv,
        file_name=f"trazabilidad_{datetime.now().strftime('%d-%m-%Y')}.csv",
        mime="text/csv",
    )
else:
    st.info("El registro comenzará a las 21:00 hs.")
