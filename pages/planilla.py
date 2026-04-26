"""
🏀 Mesa de Control - Vista Planilla
Interfaz tipo planilla de papel para carga de estadísticas
"""
import streamlit as st
import sys
import os
import time

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import (
    init_db, obtener_partido, listar_jugadores, obtener_stats_partido,
    obtener_puntos_equipo, registrar_evento, obtener_ultimos_eventos,
    borrar_ultimo_evento, guardar_puntaje_cuarto, obtener_puntaje_cuartos,
    ingresar_jugador_cancha, sacar_jugador_cancha, obtener_en_cancha,
    obtener_tiempo_total, obtener_cuartos_jugados,
    registrar_tiempo_muerto, contar_tiempos_muertos,
    actualizar_estado_partido
)

st.set_page_config(page_title="Mesa de Control - Planilla", page_icon="📋", layout="wide")

# Verificar acceso (simplificado)
if "planilla_access" not in st.session_state:
    st.session_state.planilla_access = False

if not st.session_state.planilla_access:
    st.warning("🔒 Ingresá la contraseña de mesa de control")
    
    # Verificar si existe usuario mesero, si no, crear uno por defecto
    from db import get_connection, crear_usuario
    import hashlib
    
    conn = get_connection()
    row = conn.execute("SELECT username FROM usuarios WHERE username='mesero'").fetchone()
    conn.close()
    
    if not row:
        # Crear usuario mesero con contraseña "mesero123"
        try:
            crear_usuario("mesero", "mesero123", "Mesa de Control", "mesero")
            st.info("✅ Usuario 'mesero' creado con contraseña: mesero123")
        except Exception as e:
            st.error(f"Error creando usuario: {e}")
    
    pwd = st.text_input("Contraseña", type="password")
    
    if st.button("Ingresar"):
        conn = get_connection()
        row = conn.execute("SELECT password FROM usuarios WHERE username='mesero'").fetchone()
        conn.close()
        
        if row:
            pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
            if pwd_hash == row['password']:
                st.session_state.planilla_access = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
        else:
            st.error("Error: No se pudo crear el usuario mesero")
    st.stop()

# CSS para estilo planilla
st.markdown("""
<style>
    .planilla-header {
        background: #1a1a2e;
        color: white;
        padding: 10px;
        text-align: center;
        font-weight: bold;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .equipo-header {
        background: #2d3748;
        color: white;
        padding: 8px;
        text-align: center;
        font-weight: bold;
        border-radius: 5px;
    }
    .jugador-row {
        display: flex;
        align-items: center;
        padding: 3px;
        border-bottom: 1px solid #e2e8f0;
    }
    .falta-box {
        width: 20px;
        height: 20px;
        border: 1px solid #333;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin: 0 2px;
        font-size: 10px;
        cursor: pointer;
    }
    .falta-vacia { background: white; }
    .falta-marcada { background: #e53e3e; color: white; }
    .dorsal-box {
        width: 30px;
        height: 25px;
        background: #3182ce;
        color: white;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        border-radius: 3px;
        margin-right: 5px;
    }
    .nombre-jugador {
        flex: 1;
        font-size: 13px;
    }
    .cuarto-actual {
        background: #48bb78 !important;
        color: white !important;
    }
    .marcador-box {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        background: #1a1a2e;
        color: #ffd700;
        padding: 10px;
        border-radius: 10px;
    }
    .cronometro-box {
        font-size: 2.5rem;
        font-family: 'Courier New', monospace;
        text-align: center;
        background: #000;
        color: #0f0;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

init_db()

st.title("📋 Mesa de Control - Vista Planilla")

# Seleccionar partido
partidos = [p for p in listar_partidos() if p['estado'] in ['Pendiente', 'En curso']]
if not partidos:
    st.info("No hay partidos activos")
    st.stop()

partido_opts = {f"{p['local_nombre']} vs {p['visitante_nombre']} - {p['fecha']}": p['id'] for p in partidos}
part_sel = st.selectbox("Seleccionar Partido", list(partido_opts.keys()))
partido_id = partido_opts[part_sel]
partido = obtener_partido(partido_id)

# Inicializar estado
if f"planilla_{partido_id}" not in st.session_state:
    st.session_state[f"planilla_{partido_id}"] = {
        'cuarto': 1,
        'crono_running': False,
        'crono_start': None,
        'crono_elapsed': 0,
        'jugador_seleccionado': None
    }

estado = st.session_state[f"planilla_{partido_id}"]

# Header de la planilla
col_info, col_marcador, col_crono = st.columns([2, 2, 2])

with col_info:
    st.markdown(f"""
    <div class="planilla-header">
        LIGA BINACIONAL - {partido['categoria']}<br>
        {partido['rama']} | Juego #{partido_id}
    </div>
    """, unsafe_allow_html=True)
    st.write(f"📅 {partido['fecha']}")
    st.write(f"🏟️ {partido.get('gimnasio', 'No especificado')}")

pts_local = obtener_puntos_equipo(partido_id, partido['equipo_local_id'])
pts_visit = obtener_puntos_equipo(partido_id, partido['equipo_visitante_id'])

with col_marcador:
    st.markdown(f"""
    <div style="display: flex; justify-content: space-around; align-items: center;">
        <div style="text-align: center;">
            <div style="font-size: 0.8rem; color: #666;">{partido['local_nombre'][:15]}</div>
            <div class="marcador-box">{pts_local}</div>
        </div>
        <div style="font-size: 2rem; font-weight: bold;">VS</div>
        <div style="text-align: center;">
            <div style="font-size: 0.8rem; color: #666;">{partido['visitante_nombre'][:15]}</div>
            <div class="marcador-box">{pts_visit}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

TIEMPO_CUARTO = 600  # 10 minutos

with col_crono:
    if estado['crono_running'] and estado['crono_start']:
        elapsed = estado['crono_elapsed'] + (time.time() - estado['crono_start'])
    else:
        elapsed = estado['crono_elapsed']
    
    tiempo_restante = max(0, TIEMPO_CUARTO - elapsed)
    mins = int(tiempo_restante // 60)
    secs = int(tiempo_restante % 60)
    
    st.markdown(f"""
    <div class="cronometro-box">
        Q{estado['cuarto']} | {mins:02d}:{secs:02d}
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("▶️", key=f"play_{partido_id}"):
            if not estado['crono_running']:
                estado['crono_start'] = time.time()
                estado['crono_running'] = True
                st.rerun()
    with c2:
        if st.button("⏸️", key=f"pause_{partido_id}"):
            if estado['crono_running']:
                estado['crono_elapsed'] += time.time() - estado['crono_start']
                estado['crono_running'] = False
                st.rerun()
    with c3:
        if st.button("⏭️", key=f"fin_cuarto_{partido_id}"):
            guardar_puntaje_cuarto(partido_id, partido['equipo_local_id'], estado['cuarto'], pts_local)
            guardar_puntaje_cuarto(partido_id, partido['equipo_visitante_id'], estado['cuarto'], pts_visit)
            if estado['cuarto'] < 4:
                estado['cuarto'] += 1
            estado['crono_start'] = None
            estado['crono_elapsed'] = 0
            estado['crono_running'] = False
            st.rerun()

st.markdown("---")

# Obtener jugadores y estadísticas
jug_local = listar_jugadores(partido['equipo_local_id'])
jug_visit = listar_jugadores(partido['equipo_visitante_id'])
stats = obtener_stats_partido(partido_id)
stats_dict = {s['jugador_id']: s for s in stats}

# Función para mostrar jugador tipo planilla
def mostrar_jugador_planilla(jug, es_local, partido_id, estado):
    jug_stats = stats_dict.get(jug['id'], {})
    faltas = jug_stats.get('faltas', 0) if isinstance(jug_stats, dict) else 0
    
    cols = st.columns([1, 3, 3, 1])
    
    with cols[0]:
        st.markdown(f'<div class="dorsal-box">{jug["dorsal"]}</div>', unsafe_allow_html=True)
    
    with cols[1]:
        nombre = f"{jug.get('apellido', '')}, {jug.get('nombre', '')}" if jug.get('apellido') else jug.get('nombre_completo', jug['nombre'])
        st.markdown(f'<div class="nombre-jugador">{nombre[:20]}</div>', unsafe_allow_html=True)
    
    with cols[2]:
        # Faltas tipo planilla (5 casillas)
        for i in range(1, 6):
            if i <= faltas:
                st.markdown(f'<span class="falta-box falta-marcada">{i}</span>', unsafe_allow_html=True)
            else:
                if st.button(f"F{i}", key=f"falta_{partido_id}_{jug['id']}_{i}"):
                    registrar_evento(partido_id, jug['id'], "Falta", 0, estado['cuarto'])
                    st.rerun()
    
    with cols[3]:
        # Botón para acciones rápidas
        if st.button("⚡", key=f"acc_{partido_id}_{jug['id']}"):
            estado['jugador_seleccionado'] = jug['id']
            st.rerun()

# Mostrar equipos tipo planilla
col_eq1, col_eq2 = st.columns(2)

with col_eq1:
    st.markdown(f'<div class="equipo-header">{partido["local_nombre"]} (LOCAL)</div>', unsafe_allow_html=True)
    for jug in jug_local[:12]:  # Mostrar primeros 12
        mostrar_jugador_planilla(jug, True, partido_id, estado)

with col_eq2:
    st.markdown(f'<div class="equipo-header">{partido["visitante_nombre"]} (VISITANTE)</div>', unsafe_allow_html=True)
    for jug in jug_visit[:12]:
        mostrar_jugador_planilla(jug, False, partido_id, estado)

# Panel de acciones rápidas
if estado['jugador_seleccionado']:
    st.markdown("---")
    st.subheader("⚡ Acciones Rápidas")
    
    # Buscar info del jugador
    jug_sel = None
    for j in jug_local + jug_visit:
        if j['id'] == estado['jugador_seleccionado']:
            jug_sel = j
            break
    
    if jug_sel:
        st.write(f"Jugador seleccionado: #{jug_sel['dorsal']} {jug_sel.get('nombre_completo', jug_sel['nombre'])}")
        
        col_acc = st.columns(6)
        with col_acc[0]:
            if st.button("+1 Punto", type="primary"):
                registrar_evento(partido_id, jug_sel['id'], "+1", 1, estado['cuarto'])
                estado['jugador_seleccionado'] = None
                st.rerun()
        with col_acc[1]:
            if st.button("+2 Puntos", type="primary"):
                registrar_evento(partido_id, jug_sel['id'], "+2", 2, estado['cuarto'])
                estado['jugador_seleccionado'] = None
                st.rerun()
        with col_acc[2]:
            if st.button("+3 Puntos", type="primary"):
                registrar_evento(partido_id, jug_sel['id'], "+3", 3, estado['cuarto'])
                estado['jugador_seleccionado'] = None
                st.rerun()
        with col_acc[3]:
            if st.button("Rebote"):
                registrar_evento(partido_id, jug_sel['id'], "Rebote Defensivo", 0, estado['cuarto'])
                estado['jugador_seleccionado'] = None
                st.rerun()
        with col_acc[4]:
            if st.button("Asistencia"):
                registrar_evento(partido_id, jug_sel['id'], "Asistencia", 0, estado['cuarto'])
                estado['jugador_seleccionado'] = None
                st.rerun()
        with col_acc[5]:
            if st.button("Cancelar"):
                estado['jugador_seleccionado'] = None
                st.rerun()

# Log de eventos
st.markdown("---")
st.subheader("📝 Log de Eventos")
eventos = obtener_ultimos_eventos(partido_id, 10)
if eventos:
    for ev in eventos:
        st.write(f"🔹 Q{ev['cuarto']} | #{ev['dorsal']} {ev['jugador_nombre']} - {ev['tipo']}")
else:
    st.info("Sin eventos registrados")

# Botón volver y cerrar sesión
st.markdown("---")
col_v1, col_v2 = st.columns(2)
with col_v1:
    if st.button("⬅️ Volver a Admin"):
        st.switch_page("pages/admin.py")
with col_v2:
    if st.button("🔒 Cerrar Sesión"):
        st.session_state.planilla_access = False
        st.rerun()
