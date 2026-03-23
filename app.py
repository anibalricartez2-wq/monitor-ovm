import streamlit as st
import requests
import re
import random
import pandas as pd
import io
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia SAVC v5.5", page_icon="✈️", layout="wide")
st_autorefresh(interval=1800000, key="auto_refresh")

API_KEY = "8e7917816866402688f805f637eb54d3"
AERODROMOS = ["SAVV","SAVE","SAVT","SAWC","SAVC","SAWG","SAWE","SAWH"]
ICAO_STRING = ",".join(AERODROMOS)

# --- MOTOR DE EXTRACCIÓN AVANZADA ---

def get_token_vis(texto):
    if any(x in texto for x in ["CAVOK", "SKC", "NSC", "CLR"]): return 9999
    t_limpio = re.sub(r'\d{4}/\d{4}', '', texto)
    tokens = t_limpio.split()
    for t in tokens:
        if "/" in t or "Z" in t or t.startswith("FM") or len(t) != 4: continue
        if re.fullmatch(r'\d{4}', t): return int(t)
    return 9999

def get_cloud_ceiling(texto):
    """Extrae el techo de nubes más bajo para BKN u OVC."""
    if "CAVOK" in texto or "SKC" in texto: return 10000
    capas = re.findall(r'(BKN|OVC)(\d{3})', texto)
    if capas:
        return min(int(c[1]) * 100 for c in capas)
    return 10000

def get_wind_data(texto):
    """Extrae dirección y velocidad del viento."""
    m = re.search(r'(\d{3})(\d{2})(G\d{2})?KT', texto)
    if m:
        dir_v = int(m.group(1))
        vel_v = int(m.group(2))
        gust = int(m.group(3)[1:]) if m.group(3) else 0
        return dir_v, vel_v, gust
    return None, None, 0

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

# --- AUDITORÍA SEGÚN TABLA SMN ---

def auditar_smn(metar, taf_raw):
    alertas = []
    p_vigente = obtener_bloque_vigente(taf_raw)
    
    # 1. Visibilidad 
    vm, vp = get_token_vis(metar), get_token_vis(p_vigente)
    u_vis = [150, 350, 600, 800, 1500, 3000, 5000]
    ev_m = next((i for i, u in enumerate(u_vis) if vm < u), 8)
    ev_p = next((i for i, u in enumerate(u_vis) if vp < u), 8)
    if ev_m != ev_p and not (vm >= 9999 and vp >= 5000):
        alertas.append(f"VIS: Cambio de umbral (METAR: {vm}m / TAF: {vp}m)")

    # 2. Techo de Nubes (BKN/OVC) 
    cm, cp = get_cloud_ceiling(metar), get_cloud_ceiling(p_vigente)
    u_cld = [100, 200, 500, 1000, 1500]
    ec_m = next((i for i, u in enumerate(u_cld) if cm < u), 6)
    ec_p = next((i for i, u in enumerate(u_cld) if cp < u), 6)
    if ec_m != ec_p:
        alertas.append(f"NUBES: Techo BKN/OVC fuera de umbral (M: {cm}ft / T: {cp}ft)")

    # 3. Viento (Dirección y Velocidad) 
    dm, vm_v, gm = get_wind_data(metar)
    dp, vp_v, gp = get_wind_data(p_vigente)
    if dm and dp:
        if abs(dm - dp) >= 60 and (vm_v >= 10 or vp_v >= 10):
            alertas.append(f"VIENTO: Cambio dirección > 60° (M: {dm}° / T: {dp}°)")
        if abs(vm_v - vp_v) >= 10:
            alertas.append(f"VIENTO: Diferencia velocidad > 10kt (M: {vm_v}kt / T: {vp_v}kt)")

    return alertas, p_vigente

# --- INTERFAZ ---
st.title("✈️ Monitor de Vigilancia Meteorológica (Norma SMN)")
cols = st.columns(2)

try:
    headers = {"X-API-Key": API_KEY}
    r_id = random.randint(1, 99999)
    res_metar = requests.get(f"https://api.checkwx.com/metar/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])
    res_taf = requests.get(f"https://api.checkwx.com/taf/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])

    for i, icao in enumerate(AERODROMOS):
        m_r = next((m for m in res_metar if icao in m), None)
        t_r = next((t for t in res_taf if icao in t), None)
        
        with cols[i % 2]:
            if m_r and t_r:
                alertas, p_vigente = auditar_smn(m_r, t_r)
                color = "🟥" if alertas else "✅"
                
                with st.expander(f"{color} {icao} - Dashboard de Auditoría", expanded=True):
                    st.write("**ANÁLISIS DE ENMIENDA (Bloque Vigente):**")
                    st.info(p_vigente)
                    
                    for a in alertas:
                        st.error(a)
                    
                    st.write("**REPORTES COMPLETOS:**")
                    st.success(f"**METAR:** {m_r}")
                    st.code(f"TAF COMPLETO:\n{t_r}", language=None)
            else:
                st.warning(f"Esperando datos para {icao}...")

except Exception as e:
    st.error(f"Error: {e}")
