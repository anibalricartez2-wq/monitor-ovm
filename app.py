import streamlit as st
import requests
import pandas as pd  # <--- Corregido: importación completa
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# CSS QUIRÚRGICO: Oculta menús de código, mantiene la flecha lateral
st.markdown("""
    <style>
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stDeployButton {display:none !important;}
    [data-testid="stHeader"] {display: none !important;}
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        position: fixed !important;
        top: 10px !important;
        left: 10px !important;
        z-index: 99999 !important;
    }
    .block-container {padding-top: 3rem !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. BARRA LATERAL (CONFIGURACIÓN) ---
with st.sidebar:
    st.header("⚙️ Panel de Control")
    tema = st.selectbox("Modo de Pantalla:", ["Día", "Noche", "Sistema"], index=2)
    st.divider()
    st.info("Actualización automática cada 15 min.")
    st.caption("🚀 Desarrollado por: Gemini AI & [Tu Nombre y Apellido]")

# --- 3. CONFIGURACIÓN TÉCNICA ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Refresco cada 15 minutos
st_autorefresh(interval=900000, key="vigilancia_refresh")

if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Fecha_Hora", "OACI", "METAR", "Estado", "Motivo"])

# --- 4. MOTOR DE DATOS (METAR + TAF) ---
def obtener_datos_aero(icao_list):
    icaos = ",".join(icao_list)
    headers = {"X-API-Key": API_KEY}
    try:
        m_res = requests.get(f"https://api.checkwx.com/metar/{icaos}", headers=headers, timeout=10).json().get('data', [])
        t_res = requests.get(f"https://api.checkwx.com/taf/{icaos}", headers=headers, timeout=10).json().get('data', [])
        return m_res, t_res
    except:
        return [], []

def analizar_alerta(metar_txt):
    if "G" in metar_txt:
        return "RAFAGAS", "⚠️ ALERTA: Presencia de ráfagas detectada en el METAR."
    return "NORMAL", "✅ Condición normal de viento."

# --- 5. INTERFAZ ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")
ahora = datetime.now().strftime('%H:%M:%S')
st.write(f"Última sincronización: **{ahora}** (Reseteo API: 21:00 hs)")

metars, tafs = obtener_datos_aero(AERODROMOS)

# Mapeo de información
datos_finales = {icao: {"metar": "Sin datos", "taf": "Sin datos"} for icao in AERODROMOS}
for m in metars:
    for icao in AERODROMOS:
        if icao in m: datos_finales[icao]["metar"] = m
for t in tafs:
    for icao in AERODROMOS:
        if icao in t: datos_finales[icao]["taf"] = t

# Renderizado de Tarjetas
cols = st.columns(2)
for i, icao in enumerate(AERODROMOS):
    info = datos_finales[icao]
    estado, motivo = analizar_alerta(info["metar"])
    
    with cols[i % 2]:
        icon = "⚠️" if estado == "RAFAGAS" else "✅"
        with st.expander(f"{icon} {icao}", expanded=True):
            st.markdown("**METAR Actual:**")
            st.code(info["metar"])
            st.markdown("**TAF (Pronóstico):**")
            st.code(info["taf"])
            st.caption(f"**Estado:** {motivo}")

            # Guardar en historial si es dato nuevo
            if "SAV" in info["metar"]:
                nueva_fila = pd.DataFrame([{
                    "Fecha_Hora": ahora, 
                    "OACI": icao, 
                    "METAR": info["metar"], 
                    "Estado": estado,
                    "Motivo": motivo
                }])
                st.session_state.historial = pd.concat([st.session_state.historial, nueva_fila], ignore_index=True).drop_duplicates(subset=["OACI", "METAR"])

st.divider()

# --- 6. TRAZABILIDAD Y FIRMA ---
st.subheader("📊 Historial para Excel")
if not st.session_state.historial.empty:
    st.dataframe(st.session_state.historial.tail(10), use_container_width=True)
    csv = st.session_state.historial.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Descargar Reporte (.csv)", data=csv, file_name=f"trazabilidad_{datetime.now().strftime('%d-%m-%Y')}.csv")

# FIRMA PERSONALIZADA (Reemplazá aquí con tu nombre)
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: #6c757d; font-size: 0.9rem; padding: 20px;'>
        SISTEMA DE MONITOREO AERONÁUTICO<br>
        Desarrollado en colaboración por <b>Gemini AI</b> & <b>[ANIBAL RICARTEZ]</b><br>
        <i>Comodoro Rivadavia, Argentina - 2026</i>
    </div>
    """, 
    unsafe_allow_html=True
)
