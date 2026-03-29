import streamlit as st
import requests
import re
import random
import pandas as pd
import io
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia SAVC v6.3", page_icon="✈️", layout="wide")

# Refresco automático cada 30 minutos para monitoreo en tiempo real
st_autorefresh(interval=1800000, key="auto_refresh")

API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAWC","SAVC","SAWG","SAWE","SAWH"]
ICAO_STRING = ",".join(AERODROMOS)

# Memoria de sesión para Logs y Temperaturas Máximas
if 'log_desviaciones' not in st.session_state:
    st.session_state.log_desviaciones = []
if 'max_temps' not in st.session_state:
    st.session_state.max_temps = {} # Estructura: {'ICAO': {'valor': 25, 'hora': '18:30'}}

# --- 2. FUNCIONES DE CÁLCULO Y EXTRACCIÓN ---

def calcular_dif_angular(dir1, dir2):
    """Calcula la distancia mínima en la rosa de los vientos (Círculo de 360°)."""
    diff = abs(dir1 - dir2)
    return diff if diff <= 180 else 360 - diff

def get_token_vis(texto):
    if any(x in texto for x in ["CAVOK", "SKC", "NSC", "CLR"]): return 9999
    t_limpio = re.sub(r'\d{4}/\d{4}', '', texto)
    tokens = t_limpio.split()
    for t in tokens:
        if "/" in t or "Z" in t or t.startswith("FM") or len(t) != 4: continue
        if re.fullmatch(r'\d{4}', t): return int(t)
    return 9999

def get_cloud_ceiling(texto):
    if "CAVOK" in texto or "SKC" in texto: return 10000
    capas = re.findall(r'(BKN|OVC)(\d{3})', texto)
    if capas: return min(int(c[1]) * 100 for c in capas)
    return 10000

def get_wind_data(texto):
    m = re.search(r'(\d{3})(\d{2})(G\d{2})?KT', texto)
    if m: return int(m.group(1)), int(m.group(2))
    return None, None

def extraer_tx_taf(taf):
    match = re.search(r'TX(\d{2})/', taf)
    return int(match.group(1)) if match else None

def extraer_datos_metar(metar):
    temp_match = re.search(r'\b(\d{2})/(?:M?\d{2})\b', metar)
    hora_match = re.search(r'\d{2}(\d{4})Z', metar)
    temp = int(temp_match.group(1)) if temp_match else None
    hora = f"{hora_match.group(1)[:2]}:{hora_match.group(1)[2:]}" if hora_match else "--:--"
    return temp, hora

def get_clima_icon(metar):
    if "TS" in metar: return "⛈️"
    if "RA" in metar: return "🌧️"
    if "FG" in metar or "BR" in metar: return "🌫️"
    if any(x in metar for x in ["CAVOK", "SKC", "NSC"]): return "☀️"
    return "✈️"

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

# --- 3. MOTOR DE AUDITORÍA SMN ---

def auditar_smn(icao, metar, taf_raw):
    alertas = []
    p_vigente = obtener_bloque_vigente(taf_raw)
    
    # VIENTO (Criterio Angular corregido)
    dm, vm_v = get_wind_data(metar)
    dp, vp_v = get_wind_data(p_vigente)
    if dm is not None and dp is not None:
        dif_ang = calcular_dif_angular(dm, dp)
        if dif_ang >= 60 and (vm_v >= 10 or vp_v >= 10):
            alertas.append(f"VIENTO: Dif. Angular {dif_ang}° (M: {dm}° / T: {dp}°)")
        if abs(vm_v - vp_v) >= 10:
            alertas.append(f"VIENTO: Vel >= 10kt (M: {vm_v}kt / T: {vp_v}kt)")

    # VISIBILIDAD (Umbrales SMN)
    vm, vp = get_token_vis(metar), get_token_vis(p_vigente)
    u_vis = [150, 350, 600, 800, 1500, 3000, 5000]
    if next((i for i, u in enumerate(u_vis) if vm < u), 8) != next((i for i, u in enumerate(u_vis) if vp < u), 8) and not (vm >= 9999 and vp >= 5000):
        alertas.append(f"VIS: Cambio umbral (M: {vm}m / T: {vp}m)")

    # NUBES (Umbrales SMN para BKN/OVC)
    cm, cp = get_cloud_ceiling(metar), get_cloud_ceiling(p_vigente)
    u_cld = [100, 200, 500, 1000, 1500]
    if next((i for i, u in enumerate(u_cld) if cm < u), 6) != next((i for i, u in enumerate(u_cld) if cp < u), 6):
        alertas.append(f"NUBES: Techo fuera umbral (M: {cm}ft / T: {cp}ft)")

    # Registro en Log (Evitar duplicados)
    for a in alertas:
        entry = {"Hora (Z)": datetime.now(timezone.utc).strftime("%H:%M"), "OACI": icao, "Desviación": a, "METAR": metar}
        if not st.session_state.log_desviaciones or st.session_state.log_desviaciones[-1]["Desviación"] != a:
            st.session_state.log_desviaciones.append(entry)
            
    return alertas, p_vigente

# --- 4. INTERFAZ Y PROCESAMIENTO ---

st.title("✈️ Vigilancia SAVC: Auditoría SMN & Desvíos TX")

try:
    headers = {"X-API-Key": API_KEY}
    r_id = random.randint(1, 99999)
    res_metar = requests.get(f"https://api.checkwx.com/metar/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])
    res_taf = requests.get(f"https://api.checkwx.com/taf/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])

    cols = st.columns(2)
    reporte_tx_data = []

    for i, icao in enumerate(AERODROMOS):
        m_r = next((m for m in res_metar if icao in m), None)
        t_r = next((t for t in res_taf if icao in t), None)
        
        if m_r and t_r:
            # Auditoría Normativa
            alertas, p_vigente = auditar_smn(icao, m_r, t_r)
            status_emoji = "🟥" if alertas else "✅"
            weather_emoji = get_clima_icon(m_r)
            
            # Auditoría de Temperatura (TX)
            tx_pro = extraer_tx_taf(t_r)
            t_act, h_act = extraer_datos_metar(m_r)
            if t_act is not None:
                if icao not in st.session_state.max_temps or t_act > st.session_state.max_temps[icao]['valor']:
                    st.session_state.max_temps[icao] = {'valor': t_act, 'hora': h_act}
            
            obs = st.session_state.max_temps.get(icao, {'valor': None, 'hora': '--:--'})
            if tx_pro and obs['valor'] is not None:
                reporte_tx_data.append({
                    "OACI": icao, 
                    "TX Pronost.": f"{tx_pro}°C", 
                    "Máx. Obs.": f"{obs['valor']}°C", 
                    "Hora Máx. (Z)": obs['hora'], 
                    "Desvío": f"{obs['valor'] - tx_pro:+d}°C"
                })

            # Dibujar Dashboard
            with cols[i % 2]:
                with st.expander(f"{status_emoji} {weather_emoji} {icao}", expanded=True):
                    st.warning(f"**VIGENTE:** {p_vigente}")
                    for a in alertas: st.error(a)
                    st.success(f"**METAR:** {m_r}")
                    st.text_area(f"Secuencia TAF {icao}:", t_r, height=100, key=f"t_{icao}")

except Exception as e:
    st.error(f"Error de conexión: {e}")

# --- 5. LOGS Y REPORTES FINALES ---
st.divider()
c_audit, c_temp = st.columns(2)

with c_audit:
    st.subheader("📋 Log de Auditoría (Alertas SMN)")
    if st.session_state.log_desviaciones:
        df_log = pd.DataFrame(st.session_state.log_desviaciones)
        st.dataframe(df_log.tail(10), use_container_width=True)
        # Botón Excel Auditoría
        out_aud = io.BytesIO()
        with pd.ExcelWriter(out_aud, engine='xlsxwriter') as wr: df_log.to_excel(wr, index=False)
        st.download_button("📥 Descargar Log Alertas", out_aud.getvalue(), file_name="Log_Alertas_SMN.xlsx")
    else: st.info("No se detectan desviaciones normativas.")

with c_temp:
    st.subheader("🌡️ Verificación de Temperatura Máxima")
    if reporte_tx_data:
        df_tx = pd.DataFrame(reporte_tx_data)
        st.table(df_tx)
        # Botón Excel TX
        out_tx = io.BytesIO()
        with pd.ExcelWriter(out_tx, engine='xlsxwriter') as wr: df_tx.to_excel(wr, index=False)
        st.download_button("📥 Descargar Reporte TX", out_tx.getvalue(), file_name="Reporte_Desvio_TX.xlsx")
    else: st.info("Esperando datos de TX...")

# --- FOOTER ---
st.markdown(f"""<hr><div style="text-align: center; color: #777; font-size: 0.8rem;">
    Desarrollado en colaboración por <b>Gemini AI</b> & <b>ANIBAL RICARTERZ</b><br>
    © {datetime.now().year} - Vigilancia Aeronáutica SAVC HERRAMIENTA DESARROLLADA PARA EL AUXILIAR DE PRONOSTICOS</div>""", unsafe_allow_html=True)
