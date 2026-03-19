import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# OCULTAR SOLO LO INNECESARIO (Mantiene la Sidebar visible)
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            .stDeployButton {display:none;}
            /* Oculta el encabezado pero permite que la sidebar funcione */
            [data-testid="stHeader"] {background: rgba(0,0,0,0); height: 0rem;}
            /* Ajuste de margen superior para compensar el header oculto */
            .block-container {padding-top: 2rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (MENU DE PANTALLA) ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    tema = st.selectbox(
        "Modo de Pantalla:",
        ["Día", "Noche", "Sistema"],
        index=2
    )
    st.divider()
    st.info("El monitor se actualiza solo cada 15 minutos.")

# --- 3. CONFIGURACIÓN TÉCNICA ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Refresco automático cada 15 minutos
st_autorefresh(interval=900000, key="vigilancia_refresh")

# Gestión de Historial (Trazabilidad)
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
ahora_str = datetime.now().strftime('%H:%M:%S')
st.write(f"Última sincronización: **{ahora_str}**")

# Llamada a la API
datos_raw = obtener_datos_checkwx(AERODROMOS)

# Procesamiento de reportes
reportes_dict = {icao: "Esperando reinicio (21:00 hs)..." for icao in AERODROMOS}
nuevos_datos = []

for metar in datos_raw:
    for icao in AERODROMOS:
        if icao in metar:
            reportes_dict[icao] = metar
            estado = "RAFAGAS" if "G" in metar else "NORMAL"
            nuevos_datos.append({
                "Fecha_Hora": datetime.now().strftime('%Y-%m-%d %H:%M'),
                "OACI": icao,
                "METAR": metar,
                "Estado": estado
            })

# Guardar en el Excel de la sesión
if nuevos_datos:
    df_nuevos = pd.DataFrame(nuevos_datos)
    st.session_state.historial = pd.concat([st.session_state.historial, df_nuevos], ignore_index=True)

# Dibujar tarjetas de aeródromos
cols = st.columns(2)
for i, icao in enumerate(AERODROMOS):
    metar_txt = reportes_dict[icao]
    with cols[i % 2]:
        label_viento = "⚠️" if "G" in metar_txt else "✅"
        with st.expander(f"{label_viento} {icao}", expanded=True):
            st.code(metar_txt)

st.divider()

# --- 6. SECCIÓN DE EXCEL ---
st.subheader("📊 Historial de la Guardia (Trazabilidad)")
if not st.session_state.historial.empty:
    st.dataframe(st.session_state.historial.tail(10), use_container_width=True)
    
    csv = st.session_state.historial.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Descargar Historial para Excel (.csv)",
        data=csv,
        file_name=f"trazabilidad_{datetime.now().strftime('%d-%m-%Y')}.csv",
        mime="text/csv",
    )
else:
    st.info("El registro comenzará a las 21:00 hs cuando se reactive el cupo de la API.")
