import streamlit as st
import requests
import re
import random
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

# Nueva API KEY de respaldo y lista de aeródromos del FIR
API_KEY = "2f97472097e34789ba858c973715264b" 
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# Inicializar historial de desvíos en la sesión
if 'historial_alertas' not in st.session_state:
    st.session_state.historial_alertas = []

# Inyección de CSS para ocultar menús administrativos y limpiar la interfaz
hide_st_style = """
            <style>
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            .st-emotion-cache-1wbqy5l {display:none;}
            .block-container {padding-top: 1.5rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# CONFIGURACIÓN DE REFRESCO AUTOMÁTICO: 15 MINUTOS (900.000 ms)
st_autorefresh(interval=900000, key="datarefresh")

# --- 2. FUNCIONES TÉCNICAS Y AUDITORÍA ---
def diff_angular(d1, d2):
    """Calcula la diferencia mínima entre rumbos."""
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    """Extrae dirección, intensidad y ráfagas del METAR/TAF."""
    if not texto or "Sin datos" in texto: return None, None, None
    if "00000KT" in texto: return 0, 0, 0 # Viento Calma
    
    match = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', texto)
    if match:
        dir_v = int(match.group(1))
        vel = int(match.group(2))
        raf = int(match.group(3)[1:]) if match.group(3) else 0
        return dir_v, vel, raf
    return None, None, None

def auditar(icao, reporte, taf):
    """Compara METAR vs TAF bajo los criterios establecidos."""
    alertas = []
    dr, vr, rr = parse_viento(reporte)
    dt, vt, rt = parse_viento(taf)
    
    if vr is not None and vt is not None:
        # Criterio A: Giro de viento >= 60° (Solo si la intensidad es >= 10kt)
        if vr >= 10 or vt >= 10:
            d_ang = diff_angular(dr, dt)
            if d_ang >= 60:
                msg = f"CRIT A: Giro {d_ang}°"
                alertas.append(msg)
                st.session_state.historial_alertas.append({
                    "H_Local": datetime.now().strftime("%H:%M:%S"), 
                    "OACI": icao, "Alerta": "GIRO VTO", "Valor": f"{d_ang}°"
                })
        
        # Criterio B: Diferencia de Intensidad >= 10kt
        if abs(vr - vt) >= 10:
            msg = f"CRIT B: Dif Int {abs(vr-vt)}kt"
            alertas.append(msg)
            st.session_state.historial_alertas.append({
                "H_Local": datetime.now().strftime("%H:%M:%S"), 
                "OACI": icao, "Alerta": "INTENSIDAD", "Valor": f"{abs(vr-vt)}kt"
            })
            
    return alertas

# --- 3. INTERFAZ DE USUARIO ---
st.title("🖥️ Vigilancia FIR SAVC")

# Panel de Respaldo (Solo visible si hay alertas detectadas)
if st.session_state.historial_alertas:
    with st.expander("📊 Registro de Desvíos del Turno", expanded=False):
        df_log = pd.DataFrame(st.session_state.historial_alertas)
        st.table(df_log.tail(5)) # Muestra los últimos 5
        col_csv, col_clear = st.columns([1, 4])
        with col_csv:
            csv = df_log.to_csv(index=False).encode('utf-8')
            st.download_button("📥 DESCARGAR LOG CSV", csv, f"vigilancia_SAVC_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        with col_clear:
            if st.button("🗑️ Limpiar Historial"):
                st.session_state.historial_alertas = []
                st.rerun()

# Fila de control: Hora y botón de refresco manual
c_hora, c_refresh = st.columns([4, 1])
with c_hora:
    st.write(f"Última sincronización: **{datetime.now().strftime('%H:%M:%S')}** (Próxima en 15m)")
with c_refresh:
    if st.button("🔄 Actualizar Ahora"):
        st.rerun()

st.divider()

# Grilla de Aeródromos (2 columnas)
cols = st.columns(2)
headers = {"X-API-Key": API_KEY}

for i, icao in enumerate(AERODROMOS):
    try:
        # Usamos un hash aleatorio para evitar que el navegador guarde datos viejos (cache)
        r_hash = random.randint(1, 99999)
        
        # Pedido de METAR
        res_m = requests.get(f"https://api.checkwx.com/metar/{icao}?cache={r_hash}", headers=headers).json()
        metar = res_m.get('data', ['Sin datos'])[0]
        
        # Pedido de TAF
        res_t = requests.get(f"https://api.checkwx.com/taf/{icao}?cache={r_hash}", headers=headers).json()
        taf = res_t.get('data', ['Sin datos'])[0]
        
        # Ejecutar auditoría
        alertas = auditar(icao, metar, taf) if "Sin datos" not in [metar, taf] else []

        with cols[i % 2]:
            # El color del expander cambia visualmente si hay alertas
            estado_label = "⚠️ ALERTA" if alertas else "✅ OK"
            with st.expander(f"📍 {icao} - {estado_label}", expanded=True):
                st.caption("TAF VIGENTE:")
                st.code(taf, language="bash")
                
                if "SPECI" in metar:
                    st.warning(f"🔔 SPECI DETECTADO: `{metar}`")
                else:
                    st.markdown(f"