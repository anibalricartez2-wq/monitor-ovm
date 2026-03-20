import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# CSS REFORMULADO: Header invisible pero funcional para que la flecha responda
st.markdown("""
    <style>
    /* Ocultar menús de desarrollo y footer */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    
    /* VOLVER INVISIBLE EL HEADER PERO NO BORRARLO (Para que la flecha funcione) */
    header {
        background-color: rgba(0,0,0,0) !important;
        color: rgba(0,0,0,0) !important;
    }
    
    /* OCULTAR ESPECÍFICAMENTE EL BOTÓN DE VER CÓDIGO (DERECHA) */
    header [data-testid="stHeaderActionElements"] {
        display: none !important;
    }

    /* ASEGURAR QUE LA FLECHA DE LA IZQUIERDA SE VEA Y SEA CLIQUEABLE */
    [data-testid="stSidebarCollapsedControl"] {
        background-color: rgba(128, 128, 128, 0.2) !important;
        border-radius: 5px !important;
        color: inherit !important;
    }

    /* Espaciado para el contenido */
    .block-container {padding-top: 2rem !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (CONFIGURACIÓN) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    # OPCIÓN DE PANTALLA REESTABLECIDA
    tema = st.selectbox("Modo de Pantalla:", ["Sistema", "Día", "Noche"], index=0)
    st.divider()
    st.info("Actualización: cada 15 min.")
    st.caption(f"🚀 Desarrollado por: Gemini AI & [Tu Nombre y Apellido]")

# --- 3. CONFIGURACIÓN TÉCNICA ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

st_autorefresh(interval=900000, key="vigilancia_refresh")

if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Fecha_Hora", "OACI", "METAR", "Estado", "Motivo"])

# --- 4. MOTOR DE DATOS ---
def obtener_datos(icao_list):
    icaos = ",".join(icao_list)
    headers = {"X-API-Key": API_KEY}
    try:
        m_res = requests.get(f"https://api.checkwx.com/metar/{icaos}", headers=headers, timeout=10).json().get('data', [])
        t_res = requests.get(f"https://api.checkwx.com/taf/{icaos}", headers=headers, timeout=10).json().get('data', [])
        return m_res, t_res
    except:
        return [], []

def analizar_alerta(metar_txt):
    # Mejora: Busca "G" seguido de números (ej: 28015G25KT) para evitar falsos positivos
    if re.search(r'G\d{2}', metar_txt):
        return "RAFAGAS", "⚠️ ALERTA: Ráfagas detectadas."
    return "NORMAL", "✅ Condición normal."

# --- 5. INTERFAZ ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
ahora = datetime.now().strftime('%H:%M:%S')
st.write(f"Última sincronización: **{ahora}** (Reseteo API: 21:00 hs)")

metars, tafs = obtener_datos(AERODROMOS)

datos_finales = {icao: {"metar": "Sin datos", "taf": "Sin datos"} for icao in AERODROMOS}
for m in metars:
    for icao in AERODROMOS:
        if icao in m: datos_finales[icao]["metar"] = m
for t in tafs:
    for icao in AERODROMOS:
        if icao in t: datos_finales[icao]["taf"] = t

cols = st.columns(2)
for i, icao in enumerate(AERODROMOS):
    info = datos_finales[icao]
    estado, motivo = analizar_alerta(info["metar"])
    
    with cols[i % 2]:
        icon = "⚠️" if estado == "RAFAGAS" else "✅"
        with st.expander(f"{icon} {icao}", expanded=True):
            st.markdown("**METAR:**")
            st.code(info["metar"])
            st.markdown("**TAF:**")
            st.code(info["taf"])
            st.caption(f"**Análisis:** {motivo}")

            if "SAV" in info["metar"]:
                nueva_fila = pd.DataFrame([{"Fecha_Hora": ahora, "OACI": icao, "METAR": info["metar"], "Estado": estado, "Motivo": motivo}])
                st.session_state.historial = pd.concat([st.session_state.historial, nueva_fila], ignore_index=True).drop_duplicates(subset=["OACI", "METAR"])

st.divider()

# --- 6. HISTORIAL Y FIRMA ---
st.subheader("📊 Historial para Excel")
if not st.session_state.historial.empty:
    st.dataframe(st.session_state.historial.tail(10), use_container_width=True)
    csv = st.session_state.historial.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Reporte (.csv)", data=csv, file_name=f"trazabilidad_{datetime.now().strftime('%d-%m-%Y')}.csv")

st.markdown("---")
st.markdown(
    f"<div style='text-align: center; color: gray; font-size: 0.8rem;'>"
    f"Monitor FIR SAVC desarrollado por <b>Gemini AI</b> & <b>RICARTEZ ANIBAL</b><br>"
    f"Comodoro Rivadavia, Argentina - 2026"
    f"</div>", 
    unsafe_allow_html=True
)
