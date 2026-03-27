import streamlit as st
import requests
import re
import random
import pandas as pd
import io
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh
import google.generativeai as genai
import streamlit as st

# Configuramos la IA con la llave que copiaste
genai.configure(api_key="AIzaSyBGUbf-zLMmeL1h9_sUKQj_hYfXobXIW-E")

# Creamos el modelo (podes usar flash que es más rápido)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia SAVC v5.9", page_icon="✈️", layout="wide")

# Refresco automático cada 3 minutos (180,000 ms)
st_autorefresh(interval=180000, key="auto_refresh")

API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAWC","SAVC","SAWG","SAWE","SAWH"]
ICAO_STRING = ",".join(AERODROMOS)

if 'log_desviaciones' not in st.session_state:
    st.session_state.log_desviaciones = []

# --- 2. MOTOR DE EXTRACCIÓN Y LÓGICA CLIMÁTICA ---

def get_clima_icon(metar):
    """Asigna un ícono según fenómenos del SMN y nubosidad."""
    if "TS" in metar: return "⛈️"      # Tormenta
    if "RA" in metar: return "🌧️"      # Lluvia
    if "SN" in metar: return "❄️"      # Nieve
    if "FG" in metar or "BR" in metar: return "🌫️"  # Niebla/Bruma
    if "DS" in metar or "SS" in metar: return "🌪️"  # Tempestad de polvo/arena
    if "SQ" in metar: return "💨"      # Turbonada
    if "FC" in metar: return "🌪️"      # Nube de embudo / Tornado
    
    if "OVC" in metar: return "☁️"     # Cubierto
    if "BKN" in metar: return "🌥️"     # Nuboso
    if "SCT" in metar: return "⛅"     # Parcialmente nublado
    if "FEW" in metar: return "🌤️"     # Algo de nubes
    if any(x in metar for x in ["CAVOK", "SKC", "NSC"]): return "☀️"
    return "✈️"

def get_token_vis(texto):
    if any(x in texto for x in ["CAVOK", "SKC", "NSC", "CLR"]): return 9999
    t_limpio = re.sub(r'\d{4}/\d{4}', '', texto)
    tokens = t_limpio.split()
    for t in tokens:
        if "/" in t or "Z" in t or t.startswith("FM") or len(t) != 4: continue
        if re.fullmatch(r'\d{4}', t): return int(t)
    return 9999

def get_cloud_ceiling(texto):
    """Criterio de techo para capas BKN u OVC."""
    if "CAVOK" in texto or "SKC" in texto: return 10000
    capas = re.findall(r'(BKN|OVC)(\d{3})', texto)
    if capas:
        return min(int(c[1]) * 100 for c in capas)
    return 10000

def get_wind_data(texto):
    """Extracción de viento."""
    m = re.search(r'(\d{3})(\d{2})(G\d{2})?KT', texto)
    if m:
        dir_v = int(m.group(1))
        vel_v = int(m.group(2))
        return dir_v, vel_v
    return None, None

def obtener_bloque_vigente(taf_raw):
    ahora = datetime.now(timezone.utc)
    ref = ahora.day * 10000 + ahora.hour * 100 + ahora.minute
    cuerpo = re.sub(r'^(TAF\s+)?([A-Z]{4})\s+\d{6}Z\s+', '', taf_raw)
    partes = re.split(r'\b(FM|BECMG|TEMPO|PROB\d{2})\b', cuerpo)
    vigente = partes[0] 
    for i in range(1, len(partes), 2):
        ind, cont = partes[i], partes[i+1]
        m_r = re.search(r'(\d{2})(\d{2})/(\d{2})(\d{2})', cont)
        if m_r:
            di, hi, df, hf = map(int, m_r.groups())
            if (di * 10000 + hi * 100) <= ref < (df * 10000 + hf * 100): 
                vigente = f"{ind} {cont}"
    return vigente.strip()

# --- 3. AUDITORÍA NORMATIVA SMN ---

def auditar_smn(icao, metar, taf_raw):
    alertas = []
    p_vigente = obtener_bloque_vigente(taf_raw)
    
    # Visibilidad
    vm, vp = get_token_vis(metar), get_token_vis(p_vigente)
    u_vis = [150, 350, 600, 800, 1500, 3000, 5000]
    ev_m = next((i for i, u in enumerate(u_vis) if vm < u), 8)
    ev_p = next((i for i, u in enumerate(u_vis) if vp < u), 8)
    if ev_m != ev_p and not (vm >= 9999 and vp >= 5000):
        alertas.append(f"VIS: Cambio umbral (M: {vm}m / T: {vp}m)")

    # Techo de Nubes
    cm, cp = get_cloud_ceiling(metar), get_cloud_ceiling(p_vigente)
    u_cld = [100, 200, 500, 1000, 1500]
    ec_m = next((i for i, u in enumerate(u_cld) if cm < u), 6)
    ec_p = next((i for i, u in enumerate(u_cld) if cp < u), 6)
    if ec_m != ec_p:
        alertas.append(f"NUBES: Techo fuera umbral (M: {cm}ft / T: {cp}ft)")

    # Viento
    dm, vm_v = get_wind_data(metar)
    dp, vp_v = get_wind_data(p_vigente)
    if dm is not None and dp is not None:
        if abs(dm - dp) >= 60 and (vm_v >= 10 or vp_v >= 10):
            alertas.append(f"VIENTO: Dir >= 60° (M: {dm}° / T: {dp}°)")
        if abs(vm_v - vp_v) >= 10:
            alertas.append(f"VIENTO: Vel >= 10kt (M: {vm_v}kt / T: {vp_v}kt)")

    for a in alertas:
        entry = {
            "Hora (UTC)": datetime.now(timezone.utc).strftime("%H:%M"),
            "OACI": icao,
            "Desviación": a,
            "METAR": metar
        }
        if not st.session_state.log_desviaciones or \
           not (st.session_state.log_desviaciones[-1]["OACI"] == icao and \
                st.session_state.log_desviaciones[-1]["Desviación"] == a):
            st.session_state.log_desviaciones.append(entry)

    return alertas, p_vigente

# --- 4. INTERFAZ ---

st.title("✈️ Vigilancia FIR SAVC (Norma SMN)")

try:
    headers = {"X-API-Key": API_KEY}
    r_id = random.randint(1, 99999)
    res_metar = requests.get(f"https://api.checkwx.com/metar/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])
    res_taf = requests.get(f"https://api.checkwx.com/taf/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])

    cols = st.columns(2)
    for i, icao in enumerate(AERODROMOS):
        m_r = next((m for m in res_metar if icao in m), None)
        t_r = next((t for t in res_taf if icao in t), None)
        
        with cols[i % 2]:
            if m_r and t_r:
                alertas, p_vigente = auditar_smn(icao, m_r, t_r)
                status_emoji = "🟥" if alertas else "✅"
                weather_emoji = get_clima_icon(m_r)
                
                with st.expander(f"{status_emoji} {weather_emoji} {icao}", expanded=True):
                    st.warning(f"**VIGENTE:** {p_vigente}")
                    for a in alertas: st.error(a)
                    st.success(f"**METAR:** {m_r}")
                    st.text_area(f"TAF {icao}:", t_r, height=110, key=f"t_{icao}")

except Exception as e:
    st.error(f"Error: {e}")

# --- 5. LOG Y EXCEL ---
if st.session_state.log_desviaciones:
    st.divider()
    df_log = pd.DataFrame(st.session_state.log_desviaciones)
    
    output = io.BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_log.to_excel(writer, index=False, sheet_name='Log')
        excel_data = output.getvalue()
    except:
        excel_data = df_log.to_csv(index=False).encode('utf-8')

    c1, c2 = st.columns([4, 1])
    with c1: st.subheader("📊 Log de Desviaciones")
    with c2: 
        st.download_button("📥 Descargar", excel_data, 
                           file_name=f"Vigilancia_{datetime.now().strftime('%H%M')}.xlsx")
    st.table(df_log.tail(5))

# --- 6. CRÉDITOS (FOOTER) ---
st.markdown(f"""
    <hr>
    <div style="text-align: center; color: #777; font-size: 0.85rem; padding: 10px;">
        Desarrollado en colaboración por <b>Gemini AI</b> & <b>Anibal Ricartez</b><br>
        © {datetime.now().year} - HERRAMIENTA CREADA PARA AUXILIARES DE PRONOSTICO (Criterios de Enmienda CON BASES EN DOCUMENTO SMN)
    </div>
""", unsafe_allow_html=True)
