import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# CSS ESPECÍFICO PARA OCULTAR "VIEW SOURCE" Y MANTENER EL MENÚ LATERAL
st.markdown("""
    <style>
    /* Oculta el menú de hamburguesa de la derecha y el footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display:none;}
    
    /* BLOQUEO ESPECÍFICO DE BOTONES DE CÓDIGO (GitHub/View Source) */
    button[title="View source"], 
    button[title="Edit in GitHub"],
    a[href*="github.com"] {
        display: none !important;
    }

    /* MANTIENE VISIBLE LA FLECHA DEL MENÚ LATERAL */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
    }
    
    /* Ajuste de margen para que el título no quede tapado */
    .block-container {padding-top: 1rem;}
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
    st.info("Actualización automática: cada 15 min.")

# --- 3. CONFIGURACIÓN TÉCNICA ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Refresco cada 15 minutos (900.000 ms)
st_autorefresh(interval=900000, key="vigilancia_refresh")

# Historial de Sesión para Trazabilidad
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

# Obtención de datos
datos_raw = obtener_datos_checkwx(AERODROMOS)

# Mapeo de reportes
reportes = {icao: "Esperando reinicio de API (21:00 hs)..." for icao in AERODROMOS}
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

# Actualizar tabla de trazabilidad
if nuevos_logs:
    st.session_state.historial = pd.concat([st.session_state.historial, pd.DataFrame(nuevos_logs)], ignore_index=True)

# Tarjetas de aeródromos
cols = st.columns(2)
for i, icao in enumerate(AERODROMOS):
    metar_txt = reportes[icao]
    with cols[i % 2]:
        status_icon = "⚠️" if "G" in metar_txt else "✅"
        with st.expander(f"{status_icon} {icao}", expanded=True):
            st.code(metar_txt)

st.divider()

# --- 6. SECCIÓN DE EXPORTACIÓN ---
st.subheader("📊 Historial de Trazabilidad")
if not st.session_state.historial.empty:
    st.dataframe(st.session_state.historial.tail(10), use_container_width=True)
    csv = st.session_state.historial.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Reporte (.csv)",
        data=csv,
        file_name=f"trazabilidad_{datetime.now().strftime('%d-%m-%Y')}.csv",
        mime="text/csv",
    )
else:
    st.info("El registro comenzará a las 21:00 hs cuando se reactive el cupo de la API.")
