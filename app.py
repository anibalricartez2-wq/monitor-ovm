import streamlit as st
import requests
import re
import random
import pandas as pd
import io
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia SAVC v6.6", page_icon="✈️", layout="wide")

# Refresco cada 3 minutos (180,000 ms) para mantener los datos al día
st_autorefresh(interval=180000, key="auto_refresh")

API_KEY = "8e7917816866402688f805f637eb54d3"
# Tu lista exacta de 8 aeródromos
AERODROMOS = ["SAVV", "SAVE", "SAVT", "SAWC", "SAVC", "SAWG", "SAWE", "SAWH"]
ICAO_STRING = ",".join(AERODROMOS)

# --- 2. MEMORIA DE SESIÓN (Persistencia de Logs y Registro de Mayo) ---
if 'log_desviaciones' not in st.session_state:
    st.session_state.log_desviaciones = []
if 'extremas' not in st.session_state:
    st.session_state.extremas = {}
if 'registro_mayo_anibal' not in st.session_state:
    st.session_state.registro_mayo_anibal = True

# --- 3. FUNCIONES TÉCNICAS (Con blindaje ante datos nulos) ---

def calcular_dif_angular(dir1, dir2):
    if dir1 is None or dir2 is None: return 0
    diff = abs(dir1 - dir2)
    return diff if diff <= 180 else 360 - diff

def get_token_vis(texto):
    if not texto: return 9999
    if any(x in texto for x in ["CAVOK", "SKC", "NSC", "CLR"]): return 9999
    t_limpio = re.sub(r'\d{4}/\d{4}', '', texto)
    tokens = t_limpio.split()
    for t in tokens:
        if "/" in t or "Z" in t or t.startswith("FM") or len(t) != 4: continue
        if re.fullmatch(r'\d{4}', t): return int(t)
    return 9999

def get_cloud_ceiling(texto):
    if not texto or "CAVOK" in texto or "SKC" in texto: return 10000
    capas = re.findall(r'(BKN|OVC)(\d{3})', texto)
    if capas: return min(int(c[1]) * 100 for c in capas)
    return 10000

def get_wind_data(texto):
    if not texto: return None, None
    m = re.search(r'(\d{3})(\d{2})(G\d{2})?KT', texto)
    if m: return int(m.group(1)), int(m.group(2))
    return None, None

def extraer_extremas_taf(taf):
    if not taf: return None, None
    tx = re.search(r'TX(\d{2})/', taf)
    tn = re.search(r'TN(\d{2})/', taf)
    v_tx = int(tx.group(1)) if tx else None
    v_tn = int(tn.group(1)) if tn else None
    return v_tx, v_tn

def extraer_datos_metar(metar):
    if not metar: return None, "--:--"
    t_m = re.search(r'\b(\d{2})/(?:M?\d{2})\b', metar)
    h_m = re.search(r'\d{2}(\d{4})Z', metar)
    temp = int(t_m.group(1)) if t_m else None
    hora = f"{h_m.group(1)[:2]}:{h_m.group(1)[2:]}" if h_m else "--:--"
    return temp, hora

def get_clima_icon(metar):
    if not metar: return "❓"
    if "TS" in metar: return "⛈️"
    if "RA" in metar: return "🌧️"
    if "FG" in metar or "BR" in metar: return "🌫️"
    if any(x in metar for x in ["CAVOK", "SKC", "NSC"]): return "☀️"
    return "✈️"

def obtener_bloque_vigente(taf_raw):
    if not taf_raw: return "Dato no disponible"
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

# --- 4. AUDITORÍA NORMATIVA (SMN) ---

def auditar_smn(icao, metar, taf_raw):
    alertas = []
    p_vigente = obtener_bloque_vigente(taf_raw)
    
    dm, vm_v = get_wind_data(metar)
    dp, vp_v = get_wind_data(p_vigente)
    
    if dm is not None and dp is not None:
        dif_ang = calcular_dif_angular(dm, dp)
        if dif_ang >= 60 and (vm_v >= 10 or vp_v >= 10):
            alertas.append(f"VIENTO: Dif. Angular {dif_ang}° (M: {dm}° / T: {dp}°)")
        if abs(vm_v - vp_v) >= 10:
            alertas.append(f"VIENTO: Vel >= 10kt (M: {vm_v}kt / T: {vp_v}kt)")

    vm, vp = get_token_vis(metar), get_token_vis(p_vigente)
    u_vis = [150, 350, 600, 800, 1500, 3000, 5000]
    if next((i for i, u in enumerate(u_vis) if vm < u), 8) != next((i for i, u in enumerate(u_vis) if vp < u), 8) and not (vm >= 9999 and vp >= 5000):
        alertas.append(f"VIS: Cambio umbral (M: {vm}m / T: {vp}m)")

    cm, cp = get_cloud_ceiling(metar), get_cloud_ceiling(p_vigente)
    u_cld = [100, 200, 500, 1000, 1500]
    if next((i for i, u in enumerate(u_cld) if cm < u), 6) != next((i for i, u in enumerate(u_cld) if cp < u), 6):
        alertas.append(f"NUBES: Techo fuera umbral (M: {cm}ft / T: {cp}ft)")

    for a in alertas:
        entry = {"Hora (Z)": datetime.now(timezone.utc).strftime("%H:%M"), "OACI": icao, "Desviación": a, "METAR": metar}
        if not st.session_state.log_desviaciones or st.session_state.log_desviaciones[-1]["Desviación"] != a:
            st.session_state.log_desviaciones.append(entry)
    return alertas, p_vigente

# --- 5. PROCESAMIENTO E INTERFAZ ---

st.title("✈️ Vigilancia SAVC: Auditoría SMN & Térmica")

try:
    headers = {"X-API-Key": API_KEY}
    r_id = random.randint(1, 99999)
    # Intentamos conectar con la API (CheckWX)
    res_metar_raw = requests.get(f"https://api.checkwx.com/metar/{ICAO_STRING}?cache={r_id}", headers=headers, timeout=12).json()
    res_taf_raw = requests.get(f"https://api.checkwx.com/taf/{ICAO_STRING}?cache={r_id}", headers=headers, timeout=12).json()
    
    res_metar = res_metar_raw.get('data', [])
    res_taf = res_taf_raw.get('data', [])

    cols = st.columns(2)
    reporte_termico = []

    for i, icao in enumerate(AERODROMOS):
        # Buscamos el reporte específico
        m_r = next((m for m in res_metar if icao in m), None)
        t_r = next((t for t in res_taf if icao in t), None)
        
        # --- BLINDAJE CONTRA RESPUESTA VACÍA ---
        if not m_r or not t_r:
            with cols[i % 2]:
                st.warning(f"⚠️ {icao}: Sin respuesta de API (Verificar SMN)")
            continue

        # 1. Auditoría
        alertas, p_vigente = auditar_smn(icao, m_r, t_r)
        status_emoji = "🟥" if alertas else "✅"
        
        # 2. Extremas y Temperatura Actual
        tx_p, tn_p = extraer_extremas_taf(t_r)
        t_act, h_act = extraer_datos_metar(m_r)
        
        if t_act is not None:
            if icao not in st.session_state.extremas:
                st.session_state.extremas[icao] = {'max': t_act, 'h_max': h_act, 'min': t_act, 'h_min': h_act}
            else:
                if t_act > st.session_state.extremas[icao]['max']:
                    st.session_state.extremas[icao].update({'max': t_act, 'h_max': h_act})
                if t_act < st.session_state.extremas[icao]['min']:
                    st.session_state.extremas[icao].update({'min': t_act, 'h_min': h_act})
        
        ext = st.session_state.extremas.get(icao, {})
        v_max, v_min = ext.get('max', '--'), ext.get('min', '--')
        h_max, h_min = ext.get('h_max', '--'), ext.get('h_min', '--')

        # 3. Datos para el Reporte de Tabla
        txt_err_tx = f"{(v_max - tx_p):+d}" if (isinstance(v_max, int) and tx_p is not None) else "-"
        txt_err_tn = f"{(v_min - tn_p):+d}" if (isinstance(v_min, int) and tn_p is not None) else "-"
        
        reporte_termico.append({
            "OACI": icao,
            "TX Pron.": f"{tx_p}°" if tx_p else "-", "TX Real": f"{v_max}°", "Err TX": txt_err_tx,
            "TN Pron.": f"{tn_p}°" if tn_p else "-", "TN Real": f"{v_min}°", "Err TN": txt_err_tn
        })

        # 4. Dashboard Visual (Expander)
        with cols[i % 2]:
            weather_emoji = get_clima_icon(m_r)
            with st.expander(f"{status_emoji} {weather_emoji} {icao}", expanded=True):
                st.write(f"**Sesión:** Máx {v_max}° ({h_max}Z) | Mín {v_min}° ({h_min}Z)")
                st.warning(f"**VIGENTE:** {p_vigente}")
                for a in alertas: st.error(a)
                st.success(f"**METAR:** {m_r}")
                st.text_area(f"TAF {icao}:", t_r, height=80, key=f"t_{icao}")

except Exception as e:
    st.error(f"Error General: No se pudieron obtener datos. Verifique conexión.")

# --- 6. LOGS Y REPORTES ---
st.divider()
c_audit, c_term = st.columns(2)

with c_audit:
    st.subheader("📋 Log SMN (Viento/Vis/Nub)")
    if st.session_state.log_desviaciones:
        df_log = pd.DataFrame(st.session_state.log_desviaciones)
        st.dataframe(df_log.tail(10), use_container_width=True)
        out_a = io.BytesIO()
        with pd.ExcelWriter(out_a, engine='xlsxwriter') as wr: df_log.to_excel(wr, index=False)
        st.download_button("📥 Descargar Log Alertas", out_a.getvalue(), file_name="Log_SMN_Alertas.xlsx")
    else: st.info("No hay alertas registradas en esta sesión.")

with c_term:
    st.subheader("🌡️ Reporte Térmico (TX/TN)")
    if reporte_termico:
        df_term = pd.DataFrame(reporte_termico)
        st.table(df_term)
        out_t = io.BytesIO()
        with pd.ExcelWriter(out_t, engine='xlsxwriter') as wr: df_term.to_excel(wr, index=False)
        st.download_button("📥 Descargar Reporte TX/TN", out_t.getvalue(), file_name="Reporte_Termico.xlsx")
    else: st.info("Esperando datos térmicos de mayo...")

# Créditos
st.markdown(f"""<hr><div style="text-align: center; color: #777; font-size: 0.8rem;">
    Desarrollado en colaboración por <b>Gemini AI</b> & <b>ANIBAL RICARTEZ</b><br>
    © {datetime.now().year} - Vigilancia Aeronáutica SAVC | HERRAMIENTA DISEÑADA PARA AUXILIARES DE PRONOSTICO</div>""", unsafe_allow_html=True)
