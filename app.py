import streamlit as st
import requests
import re
import random
import pandas as pd
import io
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Vigilancia SAVC v6.8", page_icon="✈️", layout="wide")

# Refresco cada 30 minutos (1,800,000 ms)
st_autorefresh(interval=1800000, key="auto_refresh")

API_KEY = "8e7917816866402688f805f637eb54d3"

# Segmentación de Aeródromos
NACIONALES = ["SAVV", "SAVE", "SAVT", "SAWC"]
INTERNACIONALES = ["SAVC", "SAWG", "SAWE", "SAWH"]
AERODROMOS = INTERNACIONALES + NACIONALES
ICAO_STRING = ",".join(AERODROMOS)

# --- 2. MEMORIA DE SESIÓN ---
if 'log_desviaciones' not in st.session_state:
    st.session_state.log_desviaciones = []
if 'extremas' not in st.session_state:
    st.session_state.extremas = {}
if 'seleccionados' not in st.session_state:
    st.session_state.seleccionados = set()

# --- 3. FUNCIONES TÉCNICAS ---

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
    if not texto: return None, 0
    m = re.search(r'(\d{3})(\d{2})(G\d{2})?KT', texto)
    if m: return int(m.group(1)), int(m.group(2))
    return None, 0

def extraer_extremas_taf(taf):
    if not taf: return None, None
    tx = re.search(r'TX(\d{2})/', taf)
    tn = re.search(r'TN(\d{2})/', taf)
    v_tx = float(tx.group(1)) if tx else None
    v_tn = float(tn.group(1)) if tn else None
    return v_tx, v_tn

def extraer_datos_metar(metar):
    if not metar: return None, "--:--"
    t_m = re.search(r'\b(\d{2})/(?:M?\d{2})\b', metar)
    h_m = re.search(r'\d{2}(\d{4})Z', metar)
    temp = float(t_m.group(1)) if t_m else None
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

# --- 4. LÓGICA DE PROCESAMIENTO ---

st.title("✈️ Vigilancia SAVC v6.8")

try:
    headers = {"X-API-Key": API_KEY}
    r_id = random.randint(1, 99999)
    res_metar = requests.get(f"https://api.checkwx.com/metar/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])
    res_taf = requests.get(f"https://api.checkwx.com/taf/{ICAO_STRING}?cache={r_id}", headers=headers).json().get('data', [])

    reporte_termico = []

    def mostrar_grupo(lista_icao, titulo):
        st.header(titulo)
        cols = st.columns(2)
        for idx, icao in enumerate(lista_icao):
            m_r = next((m for m in res_metar if icao in m), None)
            t_r = next((t for t in res_taf if icao in t), None)
            
            with cols[idx % 2]:
                if not m_r or not t_r:
                    st.warning(f"⚠️ {icao}: Sin respuesta")
                    continue
                
                alertas, p_vigente = auditar_smn(icao, m_r, t_r)
                status_emoji = "🟥" if alertas else "✅"
                
                t_act, h_act = extraer_datos_metar(m_r)
                if t_act is not None:
                    if icao not in st.session_state.extremas:
                        st.session_state.extremas[icao] = {'max': t_act, 'h_max': h_act, 'min': t_act, 'h_min': h_act}
                    else:
                        if t_act > st.session_state.extremas[icao]['max']: st.session_state.extremas[icao].update({'max': t_act, 'h_max': h_act})
                        if t_act < st.session_state.extremas[icao]['min']: st.session_state.extremas[icao].update({'min': t_act, 'h_min': h_act})
                
                ext = st.session_state.extremas.get(icao, {})
                tx_p, tn_p = extraer_extremas_taf(t_r)
                reporte_termico.append({
                    "OACI": icao, 
                    "TX Pron": f"{tx_p:.1f}°" if tx_p is not None else "-", 
                    "TX Real": f"{ext.get('max', 0):.1f}°", 
                    "TN Pron": f"{tn_p:.1f}°" if tn_p is not None else "-", 
                    "TN Real": f"{ext.get('min', 0):.1f}°"
                })

                with st.expander(f"{status_emoji} {get_clima_icon(m_r)} {icao}", expanded=True):
                    st.write(f"**Periodo Vigente:** `{p_vigente}`")
                    st.code(f"TAF COMPLETO:\n{t_r}", language="markdown")
                    for a in alertas:
                        key_msg = f"{icao}: {a}"
                        if st.checkbox(f"Avisar: {a}", key=f"check_{icao}_{a[:15]}"):
                            st.session_state.seleccionados.add(key_msg)
                        else:
                            st.session_state.seleccionados.discard(key_msg)
                        st.error(a)
                    st.success(f"METAR: {m_r}")

    tab_inter, tab_nac = st.tabs(["🌎 Internacionales (FT)", "🇦🇷 Nacionales (FC)"])
    with tab_inter: mostrar_grupo(INTERNACIONALES, "Terminales Internacionales")
    with tab_nac: mostrar_grupo(NACIONALES, "Terminales Nacionales")

except Exception as e:
    st.error(f"Error de sistema: {e}")

# --- 5. GENERADOR DE MENSAJE ---
st.divider()
st.subheader("✉️ Generador de Mensaje para Pronóstico")
if st.session_state.seleccionados:
    lista_formateada = "\n".join([f"- {item}" for item in sorted(st.session_state.seleccionados)])
    mensaje_final = (
        "Le envío las siguientes desviaciones que detectamos para que, "
        "a su criterio, evalúe la enmienda de los siguientes aeródromos:\n\n"
        f"{lista_formateada}"
    )
    st.text_area("Copiar mensaje:", mensaje_final, height=150)
    if st.button("Limpiar Selecciones"):
        st.session_state.seleccionados.clear()
        st.rerun()
else:
    st.info("Seleccione las desviaciones en los aeródromos arriba para generar el mensaje automático.")

# --- 6. LOGS Y REPORTES ---
st.divider()
c1, c2 = st.columns(2)
with c1:
    st.subheader("📋 Log de Desviaciones")
    if st.session_state.log_desviaciones:
        st.dataframe(pd.DataFrame(st.session_state.log_desviaciones).tail(10), use_container_width=True)
    else: st.info("Sin registros.")

with c2:
    st.subheader("🌡️ Comparativa Térmica (Mayo 2026)")
    if reporte_termico:
        st.table(pd.DataFrame(reporte_termico))

# Créditos
st.markdown(f"""<hr><div style="text-align: center; color: #777; font-size: 0.8rem;">
    Desarrollado en colaboración por <b>Gemini AI</b> & <b>ANIBAL FERREIRA</b><br>
    © {datetime.now().year} - Vigilancia Aeronáutica SAVC | Auxiliares de Pronóstico</div>""", unsafe_allow_html=True)
