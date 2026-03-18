import streamlit as st
import requests
import re
import random
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Vigilancia FIR SAVC", page_icon="✈️", layout="wide")

if 'historial_alertas' not in st.session_state:
    st.session_state.historial_alertas = []

hide_st_style = """
            <style>
            .stDeployButton {display:none;}
            footer {visibility: hidden;}
            .st-emotion-cache-1wbqy5l {display:none;}
            .block-container {padding-top: 1rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st_autorefresh(interval=120000, key="datarefresh")

API_KEY = "1c208dc6ec9442cd97575bdf518fb4a9"
AERODROMOS = ["SAVV","SAVE","SAVT","SAVC","SAWC","SAWG","SAWE","SAWH"]

# --- 2. FUNCIONES TÉCNICAS ---
def diff_angular(d1, d2):
    diff = abs(d1 - d2)
    return diff if diff <= 180 else 360 - diff

def parse_viento(texto):
    if not texto or "Sin datos" in texto: return None, None, None
    match = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', texto)
    if match:
        dir_v = int(match.group(1))
        vel = int(match.group(2))
        raf = int(match.group(3)[1:]) if match.group(3) else 0
        return dir_v, vel, raf
    return None, None, None

def crear_grafico_viento(dir_taf, vel_taf, dir_metar, vel_metar):
    """Genera una Rosa de los Vientos comparativa."""
    fig = go.Figure()
    # Flecha TAF (Azul)
    fig.add_trace(go.Scatterpolar(
        r=[0, vel_taf], theta=[0, dir_taf],
        mode='lines+markers', name='TAF',
        line=dict(color='blue', width=4), marker=dict(size=8)
    ))
    # Flecha METAR (Roja)
    fig.add_trace(go.Scatterpolar(
        r=[0, vel_metar], theta=[0, dir_metar],
        mode='lines+markers', name='ACTUAL',
        line=dict(color='red', width=4), marker=dict(size=10)
    ))
    fig.update_layout(
        polar=dict(angularaxis=dict(rotation=90, direction="clockwise", tickvals=[0,90,180,270], ticktext=['N','E','S','W'])),
        showlegend=False, height=250, margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def auditar(icao, reporte, taf):
    alertas = []
    dr, vr, rr = parse_viento(reporte)
    dt, vt, rt = parse_viento(taf)
    if vr is not None and vt is not None:
        if vr >= 10 or vt >= 10:
            d_ang = diff_angular(dr, dt)
            if d_ang >= 60:
                msg = f"CRIT A: Giro {d_ang}°"
                alertas.append(msg)
                st.session_state.historial_alertas.append({"H_Local": datetime.now().strftime("%H:%M:%S"), "OACI": icao, "Alerta": "GIRO VTO", "Valor": f"{d_ang}°"})
        if abs(vr - vt) >= 10:
            msg = f"CRIT B: Dif Int {abs(vr-vt)}kt"
            alertas.append(msg)
            st.session_state.historial_alertas.append({"H_Local": datetime.now().strftime("%H:%M:%S"), "OACI": icao, "Alerta": "INTENSIDAD", "Valor": f"{abs(vr-vt)}kt"})
    return alertas, dt, vt, dr, vr

# --- 3. INTERFAZ ---
st.title("🖥️ Vigilancia FIR SAVC")

# PANEL DE RESPALDO
with st.container():
    if st.session_state.historial_alertas:
        st.subheader("📊 Registro de Desvíos del Turno")
        df_log = pd.DataFrame(st.session_state.historial_alertas)
        st.table(df_log.tail(5))
        c1, c2 = st.columns([1, 4])
        with c1:
            csv = df_log.to_csv(index=False).encode('utf-8')
            st.download_button("📥 DESCARGAR LOG CSV", csv, f"vigilancia_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")
        with c2:
            if st.button("🗑️ Limpiar"):
                st.session_state.historial_alertas = []; st.rerun()
    else:
        st.info("🔎 No se han detectado desvíos. El registro está vacío.")

st.divider()
st.write(f"Actualizado: **{datetime.now().strftime('%H:%M:%S')}**")

cols = st.columns(2)
headers = {"X-API-Key": API_KEY}

for i, icao in enumerate(AERODROMOS):
    try:
        r_hash = random.randint(1, 99999)
        res_m = requests.get(f"https://api.checkwx.com/metar/{icao}?cache={r_hash}", headers=headers).json()
        metar = res_m.get('data', ['Sin datos'])[0]
        res_t = requests.get(f"https://api.checkwx.com/taf/{icao}?cache={r_hash}", headers=headers).json()
        taf = res_t.get('data', ['Sin datos'])[0]
        
        alertas, dt, vt, dr, vr = auditar(icao, metar, taf) if "Sin datos" not in [metar, taf] else ([], None, None, None, None)

        with cols[i % 2]:
            estado = "⚠️ ALERTA" if alertas else "✅ OK"
            with st.expander(f"📍 {icao} - {estado}", expanded=True):
                # Mostramos gráfico si hay datos de viento
                if vt is not None and vr is not None:
                    st.plotly_chart(crear_grafico_viento(dt, vt, dr, vr), use_container_width=True)
                
                st.caption("TAF:")
                st.code(taf)
                st.markdown(f"**ACTUAL:** `{metar}`")
                for a in alertas: st.error(a)
    except Exception:
        st.error(f"Falla en {icao}")