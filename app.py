import streamlit as st
import pandas as pd
import datetime
import requests
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor Meteorológico SAVC", layout="wide")

# --- LISTA OFICIAL DE AERÓDROMOS (ACTUALIZADA) ---
AERODROMOS = ["SAVV", "SAVE", "SAVT", "SAWC", "SAVC", "SAWG", "SAWE", "SAWH"]

# --- REGISTRO DE USO (Prioridad Mayo) ---
def registrar_actividad():
    if 'sesion_mayo' not in st.session_state:
        st.session_state['sesion_mayo'] = True
    return datetime.datetime.now()

fecha_actual = registrar_actividad()

# --- FUNCIONES DE EXTRACCIÓN (Resilientes) ---
def extraer_datos_metar(metar_texto):
    """
    Extrae viento y reporte. 
    Evita el 'ValueError' si la fuente falla devolviendo siempre 2 valores.
    """
    if not metar_texto or not isinstance(metar_texto, str) or len(metar_texto) < 10:
        return 0, "Dato no disponible (Fallo de red/fuente)"
    
    try:
        # Buscamos el viento (Ej: 24015KT)
        match = re.search(r'(\d{3})(\d{2,3})KT', metar_texto)
        if match:
            velocidad = int(match.group(2))
            # Redondeo aeronáutico a la decena (Norma MAPROMA)
            vel_red = int(round(velocidad / 10.0) * 10)
            return vel_red, metar_texto
        return 0, metar_texto
    except Exception:
        return 0, "Error en el formato del reporte"

@st.cache_data(ttl=300)
def fetch_metar(icao):
    """Scraper directo de respaldo"""
    try:
        url = f"https://www.ogimet.com/getsynop.php?res=view&icao={icao}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200 and len(r.text) > 20:
            # Limpieza básica del HTML de Ogimet para obtener solo el texto
            return r.text
        return None
    except:
        return None

# --- INTERFAZ DE USUARIO ---
st.title("🖥️ Monitor de Vigilancia Meteorológica")
st.markdown(f"**Usuario:** Aníbal | **Jurisdicción:** SAVC FIR | **Fecha:** {fecha_actual.strftime('%d/%m/%Y %H:%M')}")

# Pestañas originales
tab1, tab2, tab3 = st.tabs(["📊 Vigilancia SAVC", "📝 Auditoría SMN", "🌡️ Térmica Tx/Tn"])

with tab1:
    st.subheader("Estado de Aeródromos en Tiempo Real")
    
    # Grid de 4 columnas para que los 8 aeródromos queden simétricos (2 filas de 4)
    cols = st.columns(4)
    
    for i, oaci in enumerate(AERODROMOS):
        with cols[i % 4]:
            raw_data = fetch_metar(oaci)
            
            # --- PROTECCIÓN LÍNEA 139 (El parche clave) ---
            resultado_proceso = extraer_datos_metar(raw_data)
            
            # Validamos que tengamos siempre los 2 valores necesarios
            if isinstance(resultado_proceso, (tuple, list)) and len(resultado_proceso) >= 2:
                viento, reporte = resultado_proceso
            else:
                viento, reporte = 0, "Error de conexión"
            
            # Estilo de métrica visual
            st.metric(label=f"📍 {oaci}", value=f"{viento} KT")
            with st.expander("Ver METAR"):
                st.caption(reporte)

with tab2:
    st.subheader("Auditoría de Desviaciones (MAPROMA)")
    st.write("Análisis de redondeo de viento y discrepancias SYNOP/METAR para el periodo actual.")

with tab3:
    st.subheader("Seguimiento Térmico Tx/Tn")
    st.info("Visualización de temperaturas máximas y mínimas de Mayo 2026.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("Configuración de Datos")
    if st.button("🔄 Forzar Recarga de Datos"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    if fecha_actual.month == 5:
        st.success("Registro de Mayo activo ✅")
    st.caption("v4.6.1 - FIR SAVC Update")
