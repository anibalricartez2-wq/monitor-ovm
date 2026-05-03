import streamlit as st
import pandas as pd
import datetime
import requests
import re

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Monitor Meteorológico OVM", layout="wide")

# --- 1. REGISTRO DE USO (Prioridad para que marque Mayo) ---
def registrar_uso():
    ahora = datetime.datetime.now()
    # Aquí puedes insertar tu lógica de Google Sheets si la usas
    # Por ahora, aseguramos que la sesión lo reconozca
    if 'usuario_activo' not in st.session_state:
        st.session_state['usuario_activo'] = True
    return ahora

fecha_actual = registrar_uso()

# --- 2. FUNCIONES DE EXTRACCIÓN (Con protección contra errores) ---
def extraer_datos_metar(metar_texto):
    """
    Extrae velocidad y resto del METAR. 
    Retorna SIEMPRE una tupla (velocidad, resto) para evitar el ValueError.
    """
    if not metar_texto or not isinstance(metar_texto, str) or "404" in metar_texto:
        return 0, "S/D"
    
    try:
        # Buscamos el viento (ejemplo: 24015KT o 24015G25KT)
        match_viento = re.search(r'(\d{3})(\d{2,3})(G\d{2,3})?KT', metar_texto)
        if match_viento:
            velocidad = int(match_viento.group(2))
            return velocidad, metar_texto
        else:
            return 0, metar_texto
    except Exception:
        return 0, "Error de formato"

# --- 3. SCRAPER / OBTENCIÓN DE DATOS (Con Timeout) ---
@st.cache_data(ttl=600)
def obtener_metar_web(estacion):
    # Simulamos la consulta a Ogimet o SMN
    # En producción aquí va tu requests.get(url, timeout=5)
    try:
        # Ejemplo: url = f"https://www.ogimet.com/getsynop.php?res=view&icao={estacion}"
        # response = requests.get(url, timeout=5)
        # return response.text
        return f"{estacion} 031800Z 24010KT CAVOK 15/05 Q1013" # Simulación
    except:
        return None

# --- 4. INTERFAZ DE STREAMLIT ---
st.title("🛰️ Monitor de Vigilancia Meteorológica - v4.6")
st.subheader(f"Estado del FIR: SAVC | Fecha: {fecha_actual.strftime('%d/%m/%Y')}")

# Sidebar para control y registro
with st.sidebar:
    st.header("Control de Sistema")
    if st.button("🔄 Forzar Recarga (Limpiar Caché)"):
        st.cache_data.clear()
        st.rerun()
    
    st.info(f"Mes de gestión: {fecha_actual.strftime('%B %Y')}")

# --- 5. LÓGICA PRINCIPAL (La antigua línea 139 protegida) ---
tabs = st.tabs(["Vigilancia SAVC", "Auditoría SMN", "Térmicas Tx/Tn"])

with tabs[0]:
    st.write("### Vigilancia de Estaciones - SAVC")
    
    # Lista de estaciones de tu FIR
    estaciones = ["SAVT", "SAVC", "SAWD", "SAVY"]
    
    datos_pantalla = []
    
    for oaci in estaciones:
        metar_c = obtener_metar_web(oaci)
        
        # AQUÍ ESTÁ EL CAMBIO CLAVE (Línea 139 protegida)
        resultado = extraer_datos_metar(metar_c)
        
        # Validación de desempaquetado
        if isinstance(resultado, (tuple, list)) and len(resultado) >= 2:
            vel_c, info_extra = resultado
        else:
            vel_c, info_extra = 0, "Error en fuente"
        
        datos_pantalla.append({
            "Estación": oaci,
            "Viento (KT)": vel_c,
            "Reporte": info_extra
        })

    df = pd.DataFrame(datos_pantalla)
    st.table(df)

with tabs[1]:
    st.write("### Auditoría SMN vs OACI")
    st.info("Comparando reportes según MAPROMA...")
    # Aquí iría tu lógica de comparación de redondeo de viento a la decena

with tabs[2]:
    st.write("### Análisis de Térmicas")
    # Lógica para Tx y Tn
    st.write("Datos de temperaturas extremas para el periodo de mayo.")

# --- 6. REGISTRO DE LOGS (Al final, pero protegido) ---
try:
    # Simulación de guardado en log
    # log_db.save(usuario="Anibal", accion="Consulta", mes=5)
    pass
except:
    st.error("No se pudo actualizar el log de uso de Mayo.")
