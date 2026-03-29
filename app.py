import streamlit as st
import requests
import re
import random
import pandas as pd
import io
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia SAVC v6.5", page_icon="✈️", layout="wide")
st_autorefresh(interval=1800000, key="auto_refresh")

API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAWC","SAVC","SAWG","SAWE","SAWH"]
ICAO_STRING = ",".join(AERODROMOS)

if 'log_desviaciones' not in st.session_state: st.session_state.log_desviaciones = []
# Memoria para extremas: { 'SAVC': {'max': 25, 'h_max': '18Z', 'min': 10, 'h_min': '06Z'} }
if 'extremas' not in st.session_state: st.session_state.extremas = {}

# --- 2. FUNCIONES DE EXTRACCIÓN ---

def extraer_extremas_taf(taf):
    """Busca TX y TN en el cuerpo del TAF."""
    tx = re.search(r'TX(\d{2})/', taf)
    tn = re.search(r'TN(\d{2})/', taf)
    return (int(tx.group(1)) if tx else None), (int(tn.group(1)) if tn else None)

def extraer_datos_metar(metar):
    t_m = re.search(r'\b(\d{2})/(?:M?\d{2})\b', metar)
    h_m = re.search(r'\d{2}(\d{4})Z', metar)
    temp = int(t_m.group(1)) if t_m else None
    hora = f"{h_m.group(1)[:2]}:{h_m.group(1)[2:]}" if h_m else "--:--"
    return temp, hora

# (Se mantienen get_token_vis, get_cloud_ceiling, get_wind_data, calcular_dif_angular de v6.3)
def calcular_dif_angular(dir1, dir2):
    diff = abs(dir1 - dir2)
    return diff if diff <= 180 else 360 - diff

# --- 3. PROCESAMIENTO ---

try:
    headers = {"X-API-Key": API_KEY}
    r_id = random.randint(1, 99999)
    res_metar = requests.get(f"https://api.checkwx.com/metar/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])
    res_taf = requests.get(f"https://api.checkwx.com/taf/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])

    for m in res_metar:
        icao = m[:4]
        t_act, h_act = extraer_datos_metar(m)
        if t_act is not None:
            if icao not in st.session_state.extremas:
                st.session_state.extremas[icao] = {'max': t_act, 'h_max': h_act, 'min': t_act, 'h_min': h_act}
            else:
                if t_act > st.session_state.extremas[icao]['max']:
                    st.session_state.extremas[icao].update({'max': t_act, 'h_max': h_act})
                if t_act < st.session_state.extremas[icao]['min']:
                    st.session_state.extremas[icao].update({'min': t_act, 'h_min': h_act})
except: pass

# --- 4. INTERFAZ ---
st.title("✈️ Vigilancia SAVC: Auditoría SMN & Extremas (TX/TN)")

reporte_termico = []
cols = st.columns(2)

for i, icao in enumerate(AERODROMOS):
    m_r = next((m for m in res_metar if icao in m), None)
    t_r = next((t for t in res_taf if icao in t), None)
    
    if m_r and t_r:
        # Lógica de Extremas
        tx_p, tn_p = extraer_extremas_taf(t_r)
        ext = st.session_state.extremas.get(icao)
        
        if ext:
            d_tx = (ext['max'] - tx_p) if tx_p is not None else None
            d_tn = (ext['min'] - tn_p) if tn_p is not None else None
            reporte_termico.append({
                "OACI": icao,
                "TX Pron.": f"{tx_p}°" if tx_p else "-", "TX Real": f"{ext['max']}°", "Err TX": f"{d_tx:+d}" if d_tx is not None else "-",
                "TN Pron.": f"{tn_p}°" if tn_p else "-", "TN Real": f"{ext['min']}°", "Err TN": f"{d_tn:+d}" if d_tn is not None else "-"
            })

        with cols[i % 2]:
            with st.expander(f"✈️ {icao}", expanded=True):
                st.write(f"**Máx:** {ext['max']}° ({ext['h_max']}Z) | **Mín:** {ext['min']}° ({ext['h_min']}Z)")
                st.success(f"**METAR:** {m_r}")
                st.text_area("TAF:", t_r, height=80, key=f"t_{icao}")

# --- 5. REPORTE FINAL ---
if reporte_termico:
    st.divider()
    st.subheader("🌡️ Balance Térmico de la Jornada (TX / TN)")
    df_temp = pd.DataFrame(reporte_termico)
    st.table(df_temp)
    
    out_t = io.BytesIO()
    with pd.ExcelWriter(out_t, engine='xlsxwriter') as wr: df_temp.to_excel(wr, index=False)
    st.download_button("📥 Descargar Reporte Térmico Completo", out_t.getvalue(), file_name="Reporte_Extremas.xlsx")

st.markdown(f"""<hr><div style="text-align: center; color: #777; font-size: 0.8rem;">
    Desarrollado en colaboración por <b>Gemini AI</b> & <b>ANIBAL RICARTEZ</b><br>
    © {datetime.now().year} - Vigilancia Aeronáutica SAVC DISEÑADA PARA AUXILIARES DE PRONOSTICOS</div>""", unsafe_allow_html=True)
