import streamlit as st
import requests
import re
import random
import pandas as pd
import io
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia & TX SAVC v6.1", page_icon="✈️", layout="wide")

# Refresco configurable: 180000 (3 min) o 1800000 (30 min)
st_autorefresh(interval=180000, key="auto_refresh")

API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAWC","SAVC","SAWG","SAWE","SAWH"]
ICAO_STRING = ",".join(AERODROMOS)

# Inicialización de memoria de sesión
if 'log_desviaciones' not in st.session_state: 
    st.session_state.log_desviaciones = []
if 'max_temps' not in st.session_state: 
    # Guarda: { 'SAVC': {'valor': 25, 'hora': '18:30'} }
    st.session_state.max_temps = {}

# --- 2. FUNCIONES DE EXTRACCIÓN ---

def extraer_tx_taf(taf):
    """Extrae la TX pronosticada del TAF."""
    match = re.search(r'TX(\d{2})/', taf)
    return int(match.group(1)) if match else None

def extraer_datos_metar(metar):
    """Extrae temperatura y hora del reporte METAR."""
    temp_match = re.search(r'\b(\d{2})/(?:M?\d{2})\b', metar)
    hora_match = re.search(r'\d{2}(\d{4})Z', metar)
    
    temp = int(temp_match.group(1)) if temp_match else None
    hora = f"{hora_match.group(1)[:2]}:{hora_match.group(1)[2:]}" if hora_match else "S/D"
    return temp, hora

def get_clima_icon(metar):
    if "TS" in metar: return "⛈️"
    if "RA" in metar: return "🌧️"
    if "FG" in metar or "BR" in metar: return "🌫️"
    if any(x in metar for x in ["CAVOK", "SKC", "NSC"]): return "☀️"
    return "✈️"

# --- 3. PROCESAMIENTO DE API ---

try:
    headers = {"X-API-Key": API_KEY}
    r_id = random.randint(1, 99999)
    res_metar = requests.get(f"https://api.checkwx.com/metar/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])
    res_taf = requests.get(f"https://api.checkwx.com/taf/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])

    # Actualizar máximas observadas
    for m in res_metar:
        icao = m[:4]
        t_actual, h_actual = extraer_datos_metar(m)
        if t_actual is not None:
            if icao not in st.session_state.max_temps or t_actual > st.session_state.max_temps[icao]['valor']:
                st.session_state.max_temps[icao] = {'valor': t_actual, 'hora': h_actual}

except Exception as e:
    st.error(f"Error de conexión: {e}")

# --- 4. INTERFAZ PRINCIPAL ---
st.title("✈️ Monitor de Vigilancia & Auditoría de TX")

cols = st.columns(2)
reporte_tx_data = []

for i, icao in enumerate(AERODROMOS):
    m_r = next((m for m in res_metar if icao in m), None)
    t_r = next((t for t in res_taf if icao in t), None)
    
    if m_r and t_r:
        tx_pro = extraer_tx_taf(t_r)
        obs = st.session_state.max_temps.get(icao, {'valor': None, 'hora': '--:--'})
        
        if tx_pro and obs['valor'] is not None:
            desvio = obs['valor'] - tx_pro
            reporte_tx_data.append({
                "OACI": icao,
                "TX Pronost.": f"{tx_pro}°C",
                "Máx. Obs.": f"{obs['valor']}°C",
                "Hora Máx. (Z)": obs['hora'],
                "Desvío": f"{desvio:+d}°C"
            })

        with cols[i % 2]:
            weather_emoji = get_clima_icon(m_r)
            with st.expander(f"{weather_emoji} {icao}", expanded=True):
                st.info(f"**Análisis de TX:** Pronosticada: {tx_pro if tx_pro else '--'}°C | Observada: {obs['valor'] if obs['valor'] else '--'}°C a las {obs['hora']}Z")
                st.success(f"**METAR:** {m_r}")
                st.text_area(f"TAF Completo:", t_r, height=100, key=f"taf_{icao}")

# --- 5. REPORTES Y DESCARGAS ---
st.divider()
c_smn, c_tx = st.columns(2)

with c_smn:
    st.subheader("📋 Auditoría SMN (Viento/Vis/Nub)")
    if st.session_state.log_desviaciones:
        df_log = pd.DataFrame(st.session_state.log_desviaciones)
        st.dataframe(df_log.tail(5), use_container_width=True)
    else:
        st.write("Sin alertas normativas.")

with c_tx:
    st.subheader("🌡️ Desvíos de Temperatura")
    if reporte_tx_data:
        df_tx = pd.DataFrame(reporte_tx_data)
        st.table(df_tx)
        
        output_tx = io.BytesIO()
        with pd.ExcelWriter(output_tx, engine='xlsxwriter') as writer:
            df_tx.to_excel(writer, index=False, sheet_name='Temperaturas')
        
        st.download_button(
            label="📥 Descargar Reporte TX (Excel)",
            data=output_tx.getvalue(),
            file_name=f"Reporte_TX_{datetime.now().strftime('%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.write("Esperando datos de TX...")

# --- FOOTER ---
st.markdown(f"""<hr><div style="text-align: center; color: #777; font-size: 0.8rem;">
    Desarrollado en colaboración por <b>Gemini AI</b> & <b>Tu Usuario</b><br>
    © {datetime.now().year} - Vigilancia Aeronáutica SAVC</div>""", unsafe_allow_html=True)
