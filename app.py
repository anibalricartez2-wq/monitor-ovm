import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# INYECCIÓN CSS NIVEL "HARD"
st.markdown("""
    <style>
    /* Ocultar el menú de hamburguesa y el footer */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    
    /* ESTO BORRA EL HEADER POR COMPLETO (DONDE ESTÁ EL VIEW SOURCE) */
    [data-testid="stHeader"] {
        display: none !important;
    }
    
    /* RE-HABILITAR LA FLECHA DEL MENÚ LATERAL EN UNA POSICIÓN NUEVA */
    /* Como borramos el header, la flecha desaparece, así que la forzamos a aparecer */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        position: fixed !important;
        top: 10px !important;
        left: 10px !important;
        z-index: 99999 !important;
        background-color: rgba(255, 255, 255, 0.5) !important;
        border-radius: 5px !important;
    }

    /* Ajuste para que el título no se pegue arriba ahora que no hay header */
    .block-container {padding-top: 3rem !important;}
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
st.write(f"Última sincronización: **{ahora}**")

datos_raw = obtener_datos_checkwx(AERODROMOS)

reportes = {icao: "Esperando reinicio (00:00utc hs)..." for icao in AERODROMOS}
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
    st.download_button(label="📥 Descargar CSV", data=csv, file_name=f"trazabilidad_{datetime.now().strftime('%d-%m-%Y')}.csv", mime="text/csv")
else:
    st.info("El registro comenzará a las 21:00 hs.")
