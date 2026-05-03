import streamlit as st
import datetime

# --- 1. REGISTRO DE USO (Al principio para que marque Mayo) ---
ahora = datetime.datetime.now()
if "registro_hecho" not in st.session_state:
    # Aquí iría tu lógica de guardado en Google Sheets/DB
    # Al ponerlo acá, se registra el uso apenas abre la app, 
    # sin importar si los datos del clima fallan después.
    st.session_state.registro_hecho = True
    print(f"Uso registrado: {ahora.strftime('%Y-%m-%d %H:%M')}")

# --- 2. FUNCIÓN DE EXTRACCIÓN PROTEGIDA ---
# Asegurate de que tu función extraer_datos_metar sea similar a esta
def extraer_datos_metar_seguro(metar_texto):
    """
    Extrae datos del METAR sin romper la app si el texto es inválido.
    """
    if not metar_texto or not isinstance(metar_texto, str):
        return 0, "S/D" # Retorna valores por defecto
    
    try:
        # Aquí va tu lógica original de procesamiento/regex
        # Ejemplo simplificado:
        # v = extraer_velocidad(metar_texto)
        # r = extraer_resto(metar_texto)
        
        # Simulamos una respuesta exitosa (ajustar a tu lógica real)
        # return v, r
        
        # IMPORTANTE: Si tu lógica actual puede fallar, metela en este try
        # Para el test, devolvemos una tupla de 2 elementos siempre:
        return 10, "CAVOK" 
        
    except Exception:
        return 0, "Error de formato"

# --- 3. LÓGICA DE VIGILANCIA SAVC (La antigua línea 139) ---
st.title("Vigilancia Meteorológica SAVC FIR")

# Simulamos la obtención del METAR (metar_c)
# Si el SMN está caído, metar_c podría ser None o un error 404
metar_c = "Aquí iría el dato obtenido de la web" 

# REEMPLAZO DE LA LÍNEA 139:
try:
    # Usamos una variable intermedia para testear el resultado
    resultado = extraer_datos_metar_seguro(metar_c)
    
    # Verificamos que Python pueda desempaquetar 2 valores
    if isinstance(resultado, (list, tuple)) and len(resultado) >= 2:
        vel_c, info_extra = resultado[0], resultado[1]
    else:
        # Si la función devolvió solo 1 cosa o nada
        vel_c, info_extra = 0, "Datos incompletos"
        
except Exception as e:
    # Si todo falla, la app no se cierra, solo muestra el error en esa celda
    st.warning(f"No se pudieron procesar datos para esta estación.")
    vel_c, info_extra = 0, "N/A"

# --- 4. VISUALIZACIÓN ---
col1, col2 = st.columns(2)
col1.metric("Velocidad Viento", f"{vel_c} KT")
col2.metric("Estado", info_extra)

if st.sidebar.button("Forzar Recarga de Datos"):
    st.cache_data.clear()
    st.rerun()
