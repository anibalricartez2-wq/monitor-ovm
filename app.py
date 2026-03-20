import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor FIR SAVC", layout="wide")

# --- 2. ESTILO CSS (MODO NOCHE FORZADO Y LIMPIEZA) ---
st.markdown("""
    <style>
    /* Ocultar barra de herramientas de Streamlit */
    header, footer, .stDeployButton { display: none !important; }

    /* Forzar Modo Noche */
    .stApp { background-color: #0e1117 !important; color: #fafafa !important; }
    
    /* Estilo de las tarjetas de datos */
    .stExpander { 
        border: 1px solid #30363d !important; 
        background-color: #161b22 !important; 
    }
    
    /* Ajuste de márgenes */
    .block-container { padding-top: 2rem !important; }
    
    /* Títulos en color cian para visibilidad */
    h1, h2, h3 { color: #4f8bf9 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. LÓGICA DE ANÁLISIS (CRITERIOS SMN DEL PDF) ---
def analizar_enmienda(metar_txt):
    alertas = []
    iconos_lista = []
    
    # Viento y Ráfagas (Criterio a, b, c)
    if re.search(r'G(\d{2})', metar_txt):
        alertas.append("RAFAGAS")
        iconos_lista.append("⚠️")
    
    # Tormentas (Criterio g)
    if "TS" in metar_txt:
        alertas.append("TORMENTA")
        iconos_lista.append("⛈️")
        
    # Visibilidad (Criterio e, f - Umbral 3000m)
    vis_match = re.search(r' (\d{4}) ', metar_txt)
    if vis_match and int(vis_match.group(1)) <= 3000:
        alertas.append("BAJA VIS.")
        iconos_lista.append("🌫️")

    # Fenómenos (Criterio h - RA, DZ, SN, FG, BR, VA)
    # Buscamos coincidencias aunque tengan intensidad +/-
    if any(f in metar_txt for f in ["RA", "DZ", "SN", "FG", "BR", "VA", "GR"]):
        if "BAJA VIS." not in alertas:
            alertas.append("FENOMENO")
            iconos_lista.append("🌧️")
            
    # Techo de nubes (Criterio i, j - BKN/OVC <= 1000ft)
    if any(n in metar_txt for n in ["BKN00", "OVC00", "BKN010", "OVC010"]):
        alertas.append("TECHO BAJO")
        iconos_lista.append("☁️")
    
    estado = ", ".join(alertas) if alertas else "NORMAL"
    icon_final = iconos_lista[0] if iconos_lista else "✅"
    return estado, icon_final

# --- 4. MOTOR DE DATOS ---
API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

st_autorefresh(interval=1800000, key="refresh_v10_final")

if 'historial' not in st.session_state:
    st.session_state.historial = pd.DataFrame(columns=["Hora", "OACI", "METAR", "Alerta"])

# --- 5. INTERFAZ PRINCIPAL ---
st.title("🖥️ Monitor de Vigilancia FIR SAVC")

# PANEL DE CONTROL SIEMPRE VISIBLE (En lugar de barra lateral)
with st.container():
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("⚙️ Panel Operativo")
        st.write(f"Sincronización: **{datetime.now().strftime('%H:%M:%S')}**")
        st.info("Estado: Vigilancia Activa")
    with col_b:
        with st.expander("🔍 Ver Criterios de Enmienda Aplicados (Manual SMN)", expanded=False):
            st.write("- **Viento:** Ráfagas (G) o cambios de 10kt.")
            st.write("- **Visibilidad:** Cruce de umbrales hasta 3000m.")
            st.write("- **Techo:** BKN/OVC a 1000ft o menos.")
            st.write("- **Fenómenos:** Inicio/Fin/Intensidad de RA, TS, FG, SN.")

st.divider()

# Obtención de datos
try:
    headers = {"X-API-Key": API_KEY}
    m_data = requests.get(f"https://api.checkwx.com/metar/{','.join(AERODROMOS)}", headers=headers).json().get('data', [])
    t_data = requests.get(f"https://api.checkwx.com/taf/{','.join(AERODROMOS)}", headers=headers).json().get('data', [])
except:
    m_data, t_data = [], []

datos = {icao: {"m": "Sin datos", "t": "Sin datos"} for icao in AERODROMOS}
for m in m_data:
    for icao in AERODROMOS:
        if icao in m: datos[icao]["m"] = m
for t in t_data:
    for icao in AERODROMOS:
        if icao in t: datos[icao]["t"] = t

# Grilla de Aeródromos
cols = st.columns(2)
for i, icao in enumerate(AERODROMOS):
    info = datos[icao]
    estado, icono = analizar_enmienda(info["m"])
    with cols[i % 2]:
        with st.expander(f"{icono} {icao} - {estado}", expanded=True):
            st.markdown("**METAR**")
            st.code(info["m"])
            st.markdown("**TAF**")
            st.code(info["t"])
            # Registro en historial
            if "SAV" in info["m"] and "Sin datos" not in info["m"]:
                nueva = pd.DataFrame([{"Hora": datetime.now().strftime('%H:%M'), "OACI": icao, "METAR": info["m"], "Alerta": estado}])
                st.session_state.historial = pd.concat([st.session_state.historial, nueva], ignore_index=True).drop_duplicates(subset=["OACI", "METAR"])

st.divider()
st.subheader("📊 Historial de la Guardia")
st.dataframe(st.session_state.historial.tail(10), use_container_width=True)

# CRÉDITOS
footer_html = """
<div style='text-align: center; color: #8b949e; font-size: 0.85rem; border-top: 1px solid #30363d; padding-top: 20px; margin-top: 30px;'>
    <b>Sistema de Vigilancia FIR SAVC © 2026</b><br>
    Desarrollado por <b>Gemini AI</b> & <b>Ferreira</b><br>
    <i>Control de Enmiendas TAF según Manual SMN Argentina.</i>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
