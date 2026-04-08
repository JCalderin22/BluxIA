import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta

load_dotenv()

DB_PATH = "bluxia.db"
CODIGO_SECRETO_PROFESOR = "corazon2024"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        grado TEXT DEFAULT '1ero',
        rol TEXT DEFAULT 'estudiante',
        nombre_completo TEXT DEFAULT '',
        racha INTEGER DEFAULT 0,
        progreso INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        titulo TEXT DEFAULT 'Chat Principal',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES usuarios(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS mensajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (chat_id) REFERENCES chats(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS evaluaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        materia TEXT NOT NULL,
        nombre_examen TEXT NOT NULL,
        fecha_examen DATE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES usuarios(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS documentos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        nombre_archivo TEXT NOT NULL,
        contenido TEXT,
        imagen_base64 TEXT,
        tipo TEXT DEFAULT 'texto',
        materia TEXT DEFAULT 'General',
        grado TEXT DEFAULT 'Todos',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES usuarios(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS anuncios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL,
        profesor_nombre TEXT NOT NULL,
        materia TEXT NOT NULL,
        mensaje TEXT NOT NULL,
        grados TEXT NOT NULL,
        leido INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_id) REFERENCES usuarios(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS logros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        completado INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES usuarios(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS flashcards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        frente TEXT NOT NULL,
        reverso TEXT NOT NULL,
        materia TEXT DEFAULT 'General',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES usuarios(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS tareas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        materia TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        fecha_entrega DATE,
        completada INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES usuarios(id)
    )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS horarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        dia TEXT NOT NULL,
        hora_inicio TEXT NOT NULL,
        hora_fin TEXT NOT NULL,
        materia TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES usuarios(id)
    )''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def registrar_usuario(username, password, grado, rol="estudiante", nombre_completo="", codigo_secreto=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if rol == "profesor":
        if codigo_secreto != CODIGO_SECRETO_PROFESOR:
            conn.close()
            return False, "codigo_invalido"
        grado = "Profesor"
    try:
        cursor.execute("INSERT INTO usuarios (username, password_hash, grado, rol, nombre_completo) VALUES (?, ?, ?, ?, ?)",
            (username, hash_password(password), grado, rol, nombre_completo))
        conn.commit()
        return True, "exito"
    except sqlite3.IntegrityError:
        return False, "usuario_existe"
    finally:
        conn.close()

def login_usuario(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, grado, rol, racha, nombre_completo, progreso FROM usuarios WHERE username = ? AND password_hash = ?",
        (username, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    if user:
        return {"id": user[0], "username": user[1], "grado": user[2], "rol": user[3], "racha": user[4], "nombre_completo": user[5], "progreso": user[6]}
    return None

def obtener_perfil_usuario(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username, nombre_completo, grado, rol FROM usuarios WHERE id = ?", (user_id,))
    perfil = cursor.fetchone()
    conn.close()
    if perfil:
        return {"username": perfil[0], "nombre_completo": perfil[1], "grado": perfil[2], "rol": perfil[3]}
    return None

def actualizar_perfil(user_id, nombre_completo, grado):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET nombre_completo = ?, grado = ? WHERE id = ?",
        (nombre_completo, grado, user_id))
    conn.commit()
    conn.close()

def crear_chat(user_id, titulo="Chat Principal"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chats (user_id, titulo) VALUES (?, ?)", (user_id, titulo))
    chat_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return chat_id

def obtener_chats_usuario(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, updated_at FROM chats WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
    chats = cursor.fetchall()
    conn.close()
    return [{"id": c[0], "titulo": c[1], "updated_at": c[2]} for c in chats]

def obtener_mensajes_chat(chat_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM mensajes WHERE chat_id = ? ORDER BY created_at ASC", (chat_id,))
    mensajes = cursor.fetchall()
    conn.close()
    return [{"role": m[0], "content": m[1]} for m in mensajes]

def guardar_mensaje(chat_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO mensajes (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, role, content))
    cursor.execute("UPDATE chats SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (chat_id,))
    conn.commit()
    conn.close()

def actualizar_titulo_chat(chat_id, titulo):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE chats SET titulo = ? WHERE id = ?", (titulo, chat_id))
    conn.commit()
    conn.close()

def agregar_evaluacion(user_id, materia, nombre_examen, fecha_examen):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO evaluaciones (user_id, materia, nombre_examen, fecha_examen) VALUES (?, ?, ?, ?)",
        (user_id, materia, nombre_examen, fecha_examen))
    conn.commit()
    conn.close()

def obtener_evaluaciones_usuario(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, materia, nombre_examen, fecha_examen FROM evaluaciones WHERE user_id = ? ORDER BY fecha_examen ASC", (user_id,))
    evals = cursor.fetchall()
    conn.close()
    return [{"id": e[0], "materia": e[1], "nombre": e[2], "fecha": e[3]} for e in evals]

def eliminar_evaluacion(eval_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM evaluaciones WHERE id = ?", (eval_id,))
    conn.commit()
    conn.close()

def obtener_examenes_proximos(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    hoy = datetime.now().date()
    limite = (hoy + timedelta(hours=48)).isoformat()
    cursor.execute("""SELECT materia, nombre_examen, fecha_examen FROM evaluaciones 
        WHERE user_id = ? AND fecha_examen <= ? AND fecha_examen >= ? ORDER BY fecha_examen ASC""",
        (user_id, limite, hoy.isoformat()))
    examenes = cursor.fetchall()
    conn.close()
    return [{"materia": e[0], "nombre": e[1], "fecha": e[2]} for e in examenes]

def guardar_documento(user_id, nombre_archivo, contenido=None, imagen_base64=None, tipo="texto", materia="General", grado="Todos"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO documentos (user_id, nombre_archivo, contenido, imagen_base64, tipo, materia, grado) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, nombre_archivo, contenido, imagen_base64, tipo, materia, grado))
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id

def obtener_documentos_usuario(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre_archivo, materia, tipo FROM documentos WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    docs = cursor.fetchall()
    conn.close()
    return [{"id": d[0], "nombre": d[1], "materia": d[2], "tipo": d[3]} for d in docs]

def obtener_contenido_documento(doc_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT contenido, imagen_base64, materia, tipo FROM documentos WHERE id = ?", (doc_id,))
    doc = cursor.fetchone()
    conn.close()
    if doc:
        return {"contenido": doc[0], "imagen_base64": doc[1], "materia": doc[2], "tipo": doc[3]}
    return None

def crear_anuncio(admin_id, profesor_nombre, materia, mensaje, grados):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    grados_json = json.dumps(grados) if isinstance(grados, list) else grados
    cursor.execute("INSERT INTO anuncios (admin_id, profesor_nombre, materia, mensaje, grados) VALUES (?, ?, ?, ?, ?)",
        (admin_id, profesor_nombre, materia, mensaje, grados_json))
    conn.commit()
    conn.close()

def obtener_anuncios_para_grado(grado):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, profesor_nombre, materia, mensaje, leido, created_at FROM anuncios WHERE grados LIKE ? ORDER BY created_at DESC", (f'%{grado}%',))
    anuncios = cursor.fetchall()
    conn.close()
    return [{"id": a[0], "profesor": a[1], "materia": a[2], "mensaje": a[3], "leido": a[4], "fecha": a[5]} for a in anuncios]

def marcar_anuncio_leido(anuncio_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE anuncios SET leido = 1 WHERE id = ?", (anuncio_id,))
    conn.commit()
    conn.close()

def obtener_anuncios_no_leidos(grado):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM anuncios WHERE grados LIKE ? AND leido = 0", (f'%{grado}%',))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def agregar_logro(user_id, titulo, descripcion=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logros (user_id, titulo, descripcion) VALUES (?, ?, ?)", (user_id, titulo, descripcion))
    conn.commit()
    conn.close()

def obtener_logros_usuario(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo, descripcion, completado FROM logros WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    logros = cursor.fetchall()
    conn.close()
    return [{"id": l[0], "titulo": l[1], "descripcion": l[2], "completado": l[3]} for l in logros]

def completar_logro(logro_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE logros SET completado = 1 WHERE id = ?", (logro_id,))
    cursor.execute("UPDATE usuarios SET racha = racha + 1 WHERE id = (SELECT user_id FROM logros WHERE id = ?)", (logro_id,))
    conn.commit()
    conn.close()

def obtener_racha_usuario(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT racha FROM usuarios WHERE id = ?", (user_id,))
    racha = cursor.fetchone()
    conn.close()
    return racha[0] if racha else 0

def generar_flashcards(user_id, frente, reverso, materia="General"):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO flashcards (user_id, frente, reverso, materia) VALUES (?, ?, ?, ?)", (user_id, frente, reverso, materia))
    conn.commit()
    conn.close()

def obtener_flashcards_usuario(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, frente, reverso, materia FROM flashcards WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (user_id,))
    cards = cursor.fetchall()
    conn.close()
    return [{"id": c[0], "frente": c[1], "reverso": c[2], "materia": c[3]} for c in cards]

def eliminar_flashcard(card_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM flashcards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()

def agregar_tarea(user_id, materia, descripcion, fecha_entrega=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tareas (user_id, materia, descripcion, fecha_entrega) VALUES (?, ?, ?, ?)",
        (user_id, materia, descripcion, fecha_entrega))
    conn.commit()
    conn.close()

def obtener_tareas_usuario(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, materia, descripcion, fecha_entrega, completada FROM tareas WHERE user_id = ? ORDER BY completada ASC, fecha_entrega ASC", (user_id,))
    tareas = cursor.fetchall()
    conn.close()
    return [{"id": t[0], "materia": t[1], "descripcion": t[2], "fecha": t[3], "completada": t[4]} for t in tareas]

def obtener_horario_usuario(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT dia, hora_inicio, hora_fin, materia FROM horarios WHERE user_id = ?", (user_id,))
    horario = cursor.fetchall()
    conn.close()
    return [{"dia": h[0], "inicio": h[1], "fin": h[2], "materia": h[3]} for h in horario]

def completar_tarea(tarea_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE tareas SET completada = 1 WHERE id = ?", (tarea_id,))
    cursor.execute("UPDATE usuarios SET progreso = MIN(progreso + 5, 100) WHERE id = (SELECT user_id FROM tareas WHERE id = ?)", (tarea_id,))
    conn.commit()
    conn.close()

def eliminar_tarea(tarea_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tareas WHERE id = ?", (tarea_id,))
    conn.commit()
    conn.close()

st.set_page_config(page_title="Blux IA - U.E. Corazón de Jesús", page_icon="🧠", layout="wide", initial_sidebar_state="collapsed")

# Verificar API key
OPENROUTER_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENROUTER_API_KEY:
    st.error("❌ No se encontró la variable de entorno OPENAI_API_KEY. Por favor, configura tu archivo .env con tu clave de OpenRouter.")
    st.stop()

# Inicializar base de datos con manejo de errores
try:
    init_db()
except Exception as e:
    st.error(f"❌ Error inicializando la base de datos: {e}")
    st.stop()

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODEL_NAME = "stepfun/step-3.5-flash:free"

client = OpenAI(
    base_url=OPENROUTER_BASE_URL,
    api_key=OPENROUTER_API_KEY,
    default_headers={"HTTP-Referer": "http://localhost:8501", "X-Title": "Blux IA"}
)

# ========== CSS PREMIUM CON STICKY HEADER Y GLASSMORPHISM ==========
st.markdown("""
<style>
    /* Reset y fondo */
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important; }
    [data-testid="stAppViewContainer"] { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%) !important; }
    
    /* ===== STICKY HEADER ===== */
    .sticky-header {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background: rgba(15, 23, 42, 0.95);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 16px 30px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        z-index: 9999;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    .header-left {
        display: flex;
        align-items: center;
        gap: 15px;
    }
    .header-logo {
        width: 45px;
        height: 45px;
        background: linear-gradient(135deg, #5BA4E6 0%, #4A90D9 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.6rem;
        box-shadow: 0 4px 12px rgba(91, 164, 230, 0.4);
    }
    .header-title {
        color: #ffffff;
        font-size: 1.5rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }
    .header-right {
        text-align: right;
        color: #ffffff;
    }
    .date-display {
        font-size: 1rem;
        color: #ffffff;
        font-weight: 600;
        text-shadow: 0 1px 3px rgba(0,0,0,0.3);
        background: rgba(91, 164, 230, 0.2);
        padding: 6px 14px;
        border-radius: 8px;
        display: inline-block;
        margin-top: 4px;
    }
    
    /* ===== NAVEGACIÓN TABS ===== */
    .nav-tabs-container {
        position: fixed;
        top: 77px;
        left: 0;
        right: 0;
        background: rgba(30, 41, 59, 0.95);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        padding: 0 30px;
        z-index: 9998;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .nav-tabs {
        display: flex;
        gap: 8px;
        max-width: 1200px;
        margin: 0 auto;
    }
    .nav-tab {
        padding: 12px 24px;
        background: transparent;
        border: none;
        border-radius: 12px 12px 0 0;
        cursor: pointer;
        transition: all 0.3s ease;
        font-size: 0.95rem;
        color: #cbd5e1 !important;
        font-weight: 700;
        position: relative;
        display: flex;
        align-items: center;
        gap: 8px;
        text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }
    .nav-tab:hover {
        background: rgba(255, 255, 255, 0.15);
        color: #ffffff !important;
        text-shadow: 0 1px 3px rgba(0,0,0,0.5);
    }
    .nav-tab.active {
        background: white;
        color: #1e3a8a !important;
        font-weight: 800;
        box-shadow: 0 -4px 15px rgba(0, 0, 0, 0.15);
        text-shadow: none;
    }
    .nav-tab .badge {
        background: #ef4444;
        color: white;
        font-size: 0.7rem;
        padding: 3px 8px;
        border-radius: 10px;
        font-weight: 700;
    }
    
    /* ===== CONTENIDO PRINCIPAL ===== */
    .main-content {
        margin-top: 140px;
        padding: 20px 30px;
        min-height: calc(100vh - 140px);
    }
    
    /* ===== BURBUJAS CHAT GLASSMORPHISM ===== */
    .chat-container {
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
    }
    .chat-bubble {
        max-width: 75%;
        padding: 16px 22px;
        border-radius: 24px;
        margin-bottom: 16px;
        animation: fadeIn 0.3s ease;
        line-height: 1.6;
        font-size: 1rem;
        word-wrap: break-word;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .chat-bubble-user {
        background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        color: #ffffff;
        margin-left: auto;
        border-bottom-right-radius: 8px;
        border: 2px solid rgba(29, 78, 216, 0.9);
        box-shadow: 0 4px 20px rgba(29, 78, 216, 0.5);
        font-weight: 700;
        text-shadow: 0 1px 3px rgba(0,0,0,0.4);
        padding: 18px 24px;
    }
    .chat-bubble-assistant {
        background: #ffffff;
        color: #0f172a;
        margin-right: auto;
        border-bottom-left-radius: 8px;
        border: 2px solid #e2e8f0;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
        font-weight: 700;
        text-shadow: none;
        padding: 18px 24px;
    }
    
    /* ===== INPUT CHAT FIJO ===== */
    .chat-input-wrapper {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(15, 23, 42, 0.98);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        padding: 18px 30px;
        display: flex;
        align-items: center;
        gap: 14px;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        z-index: 9997;
    }
    .chat-input {
        flex: 1;
        padding: 14px 20px;
        border: 2px solid #64748b;
        border-radius: 28px;
        font-size: 1rem;
        outline: none;
        transition: all 0.3s ease;
        background: rgba(30, 41, 59, 0.95);
        color: #ffffff;
        font-weight: 500;
    }
    .chat-input:focus {
        border-color: #5BA4E6;
        background: rgba(30, 41, 59, 1);
        box-shadow: 0 0 0 4px rgba(91, 164, 230, 0.25);
    }
    .btn-attach {
        width: 48px;
        height: 48px;
        background: #334155;
        border: none;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
        transition: all 0.3s ease;
        color: white;
    }
    .btn-attach:hover {
        background: #475569;
        transform: scale(1.05);
    }
    .btn-send {
        padding: 14px 28px;
        background: linear-gradient(135deg, #5BA4E6, #4A90D9);
        color: white;
        border: none;
        border-radius: 28px;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .btn-send:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(91, 164, 230, 0.4);
    }
    
    /* ===== TARJETAS Y CONTENEDORES ===== */
    .card {
        background: rgba(30, 41, 59, 0.8);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        margin-bottom: 20px;
    }
    .card-title {
        color: #ffffff;
        font-size: 1.4rem;
        font-weight: 800;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        gap: 10px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.4);
    }
    
    /* ===== TAREAS ===== */
    .tarea-item {
        background: rgba(30, 41, 59, 0.9);
        border-radius: 14px;
        padding: 18px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 14px;
        border-left: 4px solid #5BA4E6;
        transition: all 0.3s ease;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .tarea-item:hover {
        transform: translateX(5px);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
    }
    .tarea-check {
        width: 28px;
        height: 28px;
        border: 2.5px solid #64748b;
        border-radius: 50%;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s ease;
        flex-shrink: 0;
    }
    .tarea-check:hover {
        border-color: #5BA4E6;
        transform: scale(1.1);
    }
    .tarea-check.completada {
        background: linear-gradient(135deg, #4ADE80, #22C55E);
        border-color: #22C55E;
    }
    .tarea-materia {
        color: #60a5fa;
        font-size: 0.85rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }
    .tarea-desc {
        color: #ffffff;
        font-size: 1rem;
        font-weight: 600;
        text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    }
    .tarea-fecha {
        color: #cbd5e1;
        font-size: 0.85rem;
        font-weight: 500;
        text-shadow: 0 1px 1px rgba(0,0,0,0.3);
    }
    
    /* ===== FLASHCARDS ===== */
    .flashcard {
        background: rgba(30, 41, 59, 0.9);
        border: 2px solid #5BA4E6;
        border-radius: 18px;
        padding: 28px;
        margin-bottom: 16px;
        cursor: pointer;
        transition: all 0.3s ease;
        min-height: 100px;
        box-shadow: 0 4px 12px rgba(91, 164, 230, 0.2);
        color: #f1f5f9;
        text-align: center;
    }
    .flashcard:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(91, 164, 230, 0.3);
        border-color: #4A90D9;
    }
    
    /* ===== LOGIN ===== */
    .login-container {
        max-width: 420px;
        margin: 100px auto;
        background: white;
        border-radius: 24px;
        padding: 48px;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.12);
        border: 1px solid #e2e8f0;
    }
    .login-logo {
        text-align: center;
        font-size: 4.5rem;
        margin-bottom: 20px;
    }
    .login-title {
        text-align: center;
        color: #1e3a8a;
        font-size: 1.8rem;
        font-weight: 800;
        margin-bottom: 10px;
    }
    .login-subtitle {
        text-align: center;
        color: #64748b;
        margin-bottom: 30px;
    }
    
    /* ===== AVISOS ===== */
    .aviso-notificacion {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        border-radius: 16px;
        padding: 16px 24px;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 14px;
        box-shadow: 0 6px 20px rgba(245, 158, 11, 0.25);
        border-left: 5px solid #fef3c7;
        animation: slideDown 0.3s ease;
    }
    @keyframes slideDown {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .aviso-icon {
        width: 44px;
        height: 44px;
        background: rgba(255, 255, 255, 0.25);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.4rem;
        flex-shrink: 0;
    }
    .aviso-content {
        flex: 1;
    }
    .aviso-titulo {
        color: #ffffff;
        font-weight: 800;
        font-size: 1.05rem;
        margin-bottom: 4px;
        text-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }
    .aviso-mensaje {
        color: #fef3c7 !important;
        font-size: 0.95rem;
        line-height: 1.6;
        font-weight: 500;
        text-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }
    
    /* ===== BOTONES DE STREAMLIT ===== */
    .stButton > button {
        border-radius: 10px !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        background: linear-gradient(135deg, #5BA4E6, #4A90D9) !important;
        color: white !important;
        box-shadow: 0 4px 12px rgba(91, 164, 230, 0.3) !important;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(91, 164, 230, 0.4) !important;
    }
    button:contains("Cerrar Sesión") {
        background: linear-gradient(135deg, #ef4444, #dc2626) !important;
        color: white !important;
        border-radius: 10px !important;
        padding: 10px 24px !important;
        box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3) !important;
    }
    button:contains("Cerrar Sesión"):hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 16px rgba(239, 68, 68, 0.4) !important;
    }
    
    /* ===== FORMULARIOS ===== */
    .stForm {
        background: rgba(30, 41, 59, 0.6);
        border-radius: 16px;
        padding: 24px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .stTextInput > div > div > input {
        background: rgba(30, 41, 59, 0.95) !important;
        color: #ffffff !important;
        border: 2px solid #64748b !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        padding: 10px 14px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #5BA4E6 !important;
        box-shadow: 0 0 0 4px rgba(91, 164, 230, 0.2) !important;
        background: rgba(30, 41, 59, 1) !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: #94a3b8 !important;
        opacity: 0.8 !important;
    }
    .stSelectbox > div > div > div {
        background: rgba(30, 41, 59, 0.95) !important;
        color: #ffffff !important;
        border: 2px solid #64748b !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        padding: 10px 14px !important;
    }
    .stSelectbox > div > div > div:focus {
        border-color: #5BA4E6 !important;
        box-shadow: 0 0 0 4px rgba(91, 164, 230, 0.2) !important;
    }
    .stDateInput > div > div > input {
        background: rgba(30, 41, 59, 0.95) !important;
        color: #ffffff !important;
        border: 2px solid #64748b !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        padding: 10px 14px !important;
    }
    .stDateInput > div > div > input:focus {
        border-color: #5BA4E6 !important;
        box-shadow: 0 0 0 4px rgba(91, 164, 230, 0.2) !important;
    }
    .stTextArea > div > div > textarea {
        background: rgba(30, 41, 59, 0.95) !important;
        color: #ffffff !important;
        border: 2px solid #64748b !important;
        border-radius: 8px !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
        padding: 12px 14px !important;
    }
    .stTextArea > div > div > textarea:focus {
        border-color: #5BA4E6 !important;
        box-shadow: 0 0 0 4px rgba(91, 164, 230, 0.2) !important;
    }
    .stTextArea > div > div > textarea::placeholder {
        color: #94a3b8 !important;
        opacity: 0.8 !important;
    }
    
    /* ===== RESPONSIVE ===== */
    @media (max-width: 768px) {
        .sticky-header {
            flex-direction: column !important;
            gap: 12px !important;
            padding: 12px 20px !important;
        }
        .header-left, .header-right {
            text-align: center !important;
            width: 100% !important;
        }
        .header-title {
            font-size: 1.2rem !important;
        }
        .nav-tabs-container {
            top: 100px !important;
            padding: 0 15px !important;
        }
        .nav-tab {
            padding: 10px 16px !important;
            font-size: 0.85rem !important;
        }
        .main-content {
            margin-top: 150px !important;
            padding: 15px !important;
        }
        .chat-container {
            max-width: 95% !important;
            padding: 15px !important;
        }
        .chat-bubble {
            max-width: 90% !important;
            padding: 12px 16px !important;
        }
        .chat-input-wrapper {
            padding: 14px 20px !important;
        }
    }
    
    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar {
        width: 8px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(30, 41, 59, 0.5);
    }
    ::-webkit-scrollbar-thumb {
        background: #475569;
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #64748b;
    }
    
    /* ===== UTILIDADES ===== */
    .text-white { color: white !important; }
    .text-blue-400 { color: #60a5fa !important; }
    .mb-20 { margin-bottom: 20px; }
    .mt-20 { margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# ========== INICIALIZACIÓN DE SESIÓN ==========
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.user_id = None
    st.session_state.user_grado = None
    st.session_state.user_role = None
    st.session_state.nombre_completo = ""
    st.session_state.current_chat_id = None
    st.session_state.messages = []
    st.session_state.tab_actual = "chat"
    st.session_state.documento_contexto = None

# ========== FUNCIONES UI ==========
def show_login():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-logo">🧠</div>', unsafe_allow_html=True)
    st.markdown('<h2 class="login-title">Blux IA</h2>', unsafe_allow_html=True)
    st.markdown('<p class="login-subtitle">U.E. Corazón de Jesús - Tu tutor inteligente ✨</p>', unsafe_allow_html=True)
    
    auth_tab = st.tabs(["🔑 Iniciar Sesión", "📝 Estudiante", "👨‍🏫 Profesor"])
    
    with auth_tab[0]:
        with st.form("login_form"):
            username = st.text_input("Usuario", placeholder="Tu nombre de usuario")
            password = st.text_input("Contraseña", type="password", placeholder="Tu contraseña")
            submit = st.form_submit_button("Entrar", use_container_width=True)
            if submit and username and password:
                user = login_usuario(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.current_user = user["username"]
                    st.session_state.user_id = user["id"]
                    st.session_state.user_grado = user["grado"]
                    st.session_state.user_role = user["rol"]
                    st.session_state.nombre_completo = user.get("nombre_completo", "")
                    st.session_state.progreso = user.get("progreso", 0)
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
    
    with auth_tab[1]:
        grados = ["1ero", "2do", "3ro", "4to", "5to A", "5to B"]
        with st.form("register_estudiante"):
            new_username = st.text_input("Nombre de usuario", placeholder="Elige un nombre")
            nombre_completo = st.text_input("Nombre completo", placeholder="Tu nombre completo")
            new_password = st.text_input("Contraseña", type="password", placeholder="Elige una contraseña")
            confirm = st.text_input("Confirmar", type="password", placeholder="Repite la contraseña")
            grado = st.selectbox("Grado", grados)
            submit = st.form_submit_button("Registrarse", use_container_width=True)
            if submit and new_username and new_password and confirm:
                if new_password == confirm:
                    exito, mensaje = registrar_usuario(new_username, new_password, grado, nombre_completo=nombre_completo)
                    if exito:
                        st.success("✅ Registrado. Ahora inicia sesión.")
                    else:
                        st.error("❌ Usuario ya existe")
                else:
                    st.error("❌ Contraseñas no coinciden")
    
    with auth_tab[2]:
        with st.form("register_profesor"):
            st.markdown('<p style="color:#5BA4E6; font-size:0.85rem; text-align:center;">Registro exclusivo para profesores</p>', unsafe_allow_html=True)
            prof_username = st.text_input("Nombre de usuario", placeholder="prof_garcia")
            prof_nombre = st.text_input("Nombre completo", placeholder="Prof. María García")
            prof_password = st.text_input("Contraseña", type="password", placeholder="Elige una contraseña")
            prof_confirm = st.text_input("Confirmar", type="password", placeholder="Repite la contraseña")
            prof_codigo = st.text_input("Código secreto", type="password", placeholder="Código de profesor")
            submit_prof = st.form_submit_button("Registrarse como Profesor", use_container_width=True)
            if submit_prof and prof_username and prof_password and prof_confirm and prof_codigo:
                if prof_password == prof_confirm:
                    exito, mensaje = registrar_usuario(prof_username, prof_password, "Profesor", rol="profesor", nombre_completo=prof_nombre, codigo_secreto=prof_codigo)
                    if exito:
                        st.success("✅ Profesor registrado. Ahora inicia sesión.")
                    elif mensaje == "codigo_invalido":
                        st.error("❌ Código secreto incorrecto")
                    else:
                        st.error("❌ Usuario ya existe")
                else:
                    st.error("❌ Contraseñas no coinciden")
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_header():
    racha = obtener_racha_usuario(st.session_state.user_id)
    progreso = st.session_state.get("progreso", 0)
    anuncios_nuevos = obtener_anuncios_no_leidos(st.session_state.user_grado)
    
    # Fecha actual en español
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    ahora = datetime.now()
    fecha_espanol = f"{dias[ahora.weekday()]}, {ahora.day} de {meses[ahora.month-1]} de {ahora.year}"
    
    st.markdown(f"""
    <div class="sticky-header">
        <div class="header-left">
            <div class="header-logo">🧠</div>
            <h1 class="header-title">Blux IA</h1>
        </div>
        <div class="header-right">
            <div class="date-display">📅 {fecha_espanol}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Navegación con botones de Streamlit estilizados
    num_cols = 7 if st.session_state.user_role in ['admin', 'profesor'] else 6
    cols = st.columns(num_cols)
    badge_avisos = f" ({anuncios_nuevos})" if anuncios_nuevos > 0 else ""
    
    # Definir pestañas según rol
    if st.session_state.user_role in ['admin', 'profesor']:
        tabs = [
            ("💬 Chat", "chat"),
            ("📋 Tareas", "tareas"),
            ("📅 Horario", "horario"),
            ("🔔 Avisos", "avisos"),
            ("📚 Repaso", "repaso"),
            ("👨‍🏫 Profesor", "profesor"),
            ("⚙️ Ajustes", "ajustes")
        ]
    else:
        tabs = [
            ("💬 Chat", "chat"),
            ("📋 Tareas", "tareas"),
            ("📅 Horario", "horario"),
            ("🔔 Avisos", "avisos"),
            ("📚 Repaso", "repaso"),
            ("⚙️ Ajustes", "ajustes")
        ]
    
    # Crear botones de navegación
    for idx, (label, tab_id) in enumerate(tabs):
        with cols[idx]:
            if label == "🔔 Avisos" and badge_avisos:
                label = label + badge_avisos
            if st.button(label, use_container_width=True, type="primary" if st.session_state.tab_actual == tab_id else "secondary"):
                st.session_state.tab_actual = tab_id

def show_avisos():
    anuncios = obtener_anuncios_para_grado(st.session_state.user_grado)
    if anuncios:
        for an in anuncios:
            if not an["leido"]:
                st.markdown(f"""
<div class="aviso-notificacion">
    <div class="aviso-icon">🔔</div>
    <div class="aviso-content">
        <p class="aviso-titulo">Nuevo aviso de {an["profesor"]} ({an["materia"]}):</p>
        <p class="aviso-mensaje">{an["mensaje"]}</p>
    </div>
</div>
""", unsafe_allow_html=True)
                marcar_anuncio_leido(an["id"])

def show_chat():
    show_avisos()
    
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Usar contenedor con altura fija para evitar saltos
    chat_container = st.container()
    
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-bubble chat-bubble-user">{message["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-bubble chat-bubble-assistant">{message["content"]}</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_tareas():
    st.markdown('<h3 class="card-title">📋 Mis Tareas</h3>', unsafe_allow_html=True)
    
    with st.form("tarea_form"):
        col1, col2 = st.columns([2, 1])
        with col1:
            materia = st.text_input("Materia", placeholder="Ej: Matemáticas")
            descripcion = st.text_input("Descripción", placeholder="Ej: Ejercicios página 45")
        with col2:
            fecha = st.date_input("Fecha de entrega")
        submit = st.form_submit_button("➕ Agregar tarea")
        if submit and materia and descripcion:
            agregar_tarea(st.session_state.user_id, materia, descripcion, fecha.isoformat())
            st.success("✅ Tarea agregada")
            st.rerun()
    
    tareas = obtener_tareas_usuario(st.session_state.user_id)
    if tareas:
        for tarea in tareas:
            clase = "tarea-check completada" if tarea["completada"] else "tarea-check"
            icono = "✅" if tarea["completada"] else ""
            st.markdown(f"""
<div class="tarea-item">
    <div class="{clase}" onclick="document.getElementById('complete_{tarea['id']}').value='true'">{icono}</div>
    <div style="flex:1">
        <div class="tarea-materia">{tarea['materia']}</div>
        <div class="tarea-desc">{tarea['descripcion']}</div>
        <div class="tarea-fecha">📅 {tarea['fecha'] or 'Sin fecha'}</div>
    </div>
</div>
<input type="hidden" id="complete_{tarea['id']}" value="false">
""", unsafe_allow_html=True)
            if st.button(f"Completar", key=f"task_{tarea['id']}"):
                completar_tarea(tarea["id"])
                st.balloons()
                st.rerun()
    else:
        st.markdown('<p style="color:#94a3b8; text-align:center; padding:40px;">No hay tareas pendientes 🎉</p>', unsafe_allow_html=True)

def show_horario():
    st.markdown('<h3 class="card-title">📅 Mi Horario</h3>', unsafe_allow_html=True)
    
    horario = obtener_horario_usuario(st.session_state.user_id)
    
    if not horario:
        st.markdown('<div class="card"><div style="text-align:center; padding:20px;">', unsafe_allow_html=True)
        st.markdown('<p style="color:#cbd5e1; font-size:1.1rem; margin-bottom:20px;">No tienes horario configurado aún.</p>', unsafe_allow_html=True)
        if st.button("➕ Agregar mi primer horario", use_container_width=True):
            st.session_state.mostrar_form_horario = True
        st.markdown('</div></div>', unsafe_allow_html=True)
    
    if st.session_state.get("mostrar_form_horario", False):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        with st.form("horario_form"):
            col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
            with col1:
                dia = st.selectbox("Día", ["lunes", "martes", "miércoles", "jueves", "viernes"])
            with col2:
                materia = st.text_input("Materia", placeholder="Ej: Matemáticas")
            with col3:
                hora_inicio = st.time_input("Hora inicio", format="HH:mm")
            with col4:
                hora_fin = st.time_input("Hora fin", format="HH:mm")
            
            submit = st.form_submit_button("➕ Agregar clase", use_container_width=True)
            
            if submit and materia:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO horarios (user_id, dia, hora_inicio, hora_fin, materia) VALUES (?, ?, ?, ?, ?)",
                    (st.session_state.user_id, dia, hora_inicio.strftime("%H:%M"), hora_fin.strftime("%H:%M"), materia))
                conn.commit()
                conn.close()
                st.success("✅ Clase agregada al horario")
                st.session_state.mostrar_form_horario = False
                st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    if horario:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        
        dias = ["lunes", "martes", "miércoles", "jueves", "viernes"]
        for dia in dias:
            clases_dia = [h for h in horario if h['dia'] == dia]
            if clases_dia:
                st.markdown(f'<h4 style="color:#60a5fa; margin:15px 0 10px 0; font-size:1.1rem;">📌 {dia.capitalize()}</h4>', unsafe_allow_html=True)
                for clase in sorted(clases_dia, key=lambda x: x['inicio']):
                    st.markdown(f"""
<div style="background:#334155; padding:12px 16px; border-radius:10px; margin-bottom:8px; border-left:4px solid #5BA4E6;">
    <strong style="color:#f1f5f9;">{clase['materia']}</strong>
    <span style="color:#cbd5e1; float:right;">{clase['inicio']} - {clase['fin']}</span>
</div>
""", unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_repaso():
    st.markdown('<h3 class="card-title">📚 Centro de Repaso</h3>', unsafe_allow_html=True)
    
    with st.form("flashcard_form"):
        col1, col2 = st.columns(2)
        with col1:
            frente = st.text_input("Pregunta", placeholder="¿Qué es la fotosíntesis?")
        with col2:
            reverso = st.text_input("Respuesta", placeholder="Proceso de conversión de luz...")
        materia = st.text_input("Materia", placeholder="Biología")
        submit = st.form_submit_button("➕ Crear tarjeta")
        if submit and frente and reverso:
            generar_flashcards(st.session_state.user_id, frente, reverso, materia)
            st.success("✅ Tarjeta creada")
            st.rerun()
    
    cards = obtener_flashcards_usuario(st.session_state.user_id)
    if cards:
        for card in cards:
            with st.expander(f"📇 {card['frente'][:50]}..."):
                st.write(card['reverso'])
                if st.button(f"🗑️ Eliminar", key=f"del_fc_{card['id']}"):
                    eliminar_flashcard(card["id"])
                    st.rerun()

def show_ajustes():
    st.markdown('<h3 class="card-title">⚙️ Ajustes de Perfil</h3>', unsafe_allow_html=True)
    
    perfil = obtener_perfil_usuario(st.session_state.user_id)
    if not perfil:
        st.error("No se pudo cargar el perfil")
        return
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    with st.form("perfil_form"):
        st.markdown(f"**👤 Usuario:** `{perfil['username']}`")
        nombre_completo = st.text_input("Nombre Completo", value=perfil['nombre_completo'] or "")
        
        grados_disponibles = ["1ero", "2do", "3ro", "4to", "5to A", "5to B"]
        grado_actual = perfil['grado'] if perfil['grado'] in grados_disponibles else "1ero"
        grado = st.selectbox("Grado/Año", grados_disponibles, index=grados_disponibles.index(grado_actual))
        
        submit = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)
        
        if submit:
            actualizar_perfil(st.session_state.user_id, nombre_completo, grado)
            st.session_state.nombre_completo = nombre_completo
            st.session_state.user_grado = grado
            st.success("✅ Perfil actualizado correctamente")
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Botón cerrar sesión
    st.markdown('<div style="text-align:center; margin-top:30px;">', unsafe_allow_html=True)
    if st.button("🚪 Cerrar Sesión", use_container_width=False):
        st.session_state.logged_in = False
        st.session_state.current_user = None
        st.session_state.user_id = None
        st.session_state.user_grado = None
        st.session_state.user_role = None
        st.session_state.nombre_completo = ""
        st.session_state.current_chat_id = None
        st.session_state.messages = []
        st.session_state.tab_actual = "chat"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def show_admin_panel():
    if st.session_state.user_role not in ['admin', 'profesor']:
        return
    
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<h3 class="card-title">👨‍🏫 Panel de Profesor</h3>', unsafe_allow_html=True)
    
    with st.form("anuncio_form"):
        profesor_nombre = st.text_input("Tu nombre", value=st.session_state.nombre_completo or st.session_state.current_user)
        materia = st.text_input("Materia", placeholder="Ej: Física")
        mensaje = st.text_area("Mensaje del aviso", placeholder="Ej: Examen corto este viernes")
        grados_disponibles = ["1ero", "2do", "3ro", "4to", "5to A", "5to B", "Todos"]
        grados_sel = st.multiselect("Dirigido a", grados_disponibles, default=["Todos"])
        submit = st.form_submit_button("📤 Publicar aviso")
        if submit and mensaje and grados_sel:
            crear_anuncio(st.session_state.user_id, profesor_nombre, materia, mensaje, grados_sel)
            st.success("✅ Aviso publicado")
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def main():
    if not st.session_state.logged_in:
        show_login()
        return
    
    show_header()
    
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    if st.session_state.tab_actual == "chat":
        show_chat()
    elif st.session_state.tab_actual == "tareas":
        show_tareas()
    elif st.session_state.tab_actual == "horario":
        show_horario()
    elif st.session_state.tab_actual == "avisos":
        show_avisos()
        st.markdown('<p style="color:#64748B; text-align:center; padding:40px;">No hay más avisos nuevos</p>', unsafe_allow_html=True)
    elif st.session_state.tab_actual == "repaso":
        show_repaso()
    elif st.session_state.tab_actual == "ajustes":
        show_ajustes()
    elif st.session_state.tab_actual == "profesor":
        if st.session_state.user_role in ['admin', 'profesor']:
            show_admin_panel()
        else:
            st.error("No tienes permiso para acceder a esta página")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Input de chat fijo
    if st.session_state.tab_actual == "chat":
        st.markdown('<div class="chat-input-wrapper">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 10, 2])
        with col1:
            st.file_uploader("📎", type=["png", "jpg", "jpeg", "pdf", "txt"], label_visibility="collapsed", key="chat_upload")
        with col2:
            prompt = st.chat_input("Escribe tu mensaje...")
        with col3:
            pass
        st.markdown('</div>', unsafe_allow_html=True)
        
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            guardar_mensaje(st.session_state.current_chat_id or crear_chat(st.session_state.user_id), "user", prompt)
            
            if st.session_state.current_chat_id is None:
                st.session_state.current_chat_id = crear_chat(st.session_state.user_id)
            
            with st.spinner("Blux IA está pensando..."):
                try:
                    # Obtener contexto del usuario
                    tareas = obtener_tareas_usuario(st.session_state.user_id)
                    avisos = obtener_anuncios_para_grado(st.session_state.user_grado)
                    horario = obtener_horario_usuario(st.session_state.user_id)
                    
                    tareas_str = "\n".join([f"- {t['materia']}: {t['descripcion']} (Vence: {t['fecha']})" for t in tareas if not t['completada']])
                    avisos_str = "\n".join([f"- De {a['profesor']} ({a['materia']}): {a['mensaje']}" for a in avisos])
                    horario_str = "\n".join([f"- {h['dia']} {h['inicio']}-{h['fin']}: {h['materia']}" for h in horario])
                    
                    system_prompt = (
                        f"Eres Blux IA, un tutor inteligente y motivador de la U.E. Corazón de Jesús. "
                        f"Tu personalidad: entusiasta, empático, brillante y muy educativo. "
                        f"Usa emojis educativos (🧠, ✨, 📚, 🎯, 💪, 🚀) para hacer el aprendizaje más ameno. "
                        f"Dirígete al estudiante con cariño: usa 'campeón/a', 'estudiante estrella', 'genio', 'futuro profesional'. "
                        f"Motiva constantemente, celebra sus logros y anima a superar dificultades. "
                        f"Recuerda: Eres un tutor para secundaria en Venezuela. "
                        f"Usuario: {st.session_state.current_user} ({st.session_state.user_grado}).\n\n"
                        f"CONTEXTO DEL ESTUDIANTE:\n"
                        f"Tareas pendientes:\n{tareas_str if tareas_str else '¡No hay tareas pendientes! 🎉'}\n\n"
                        f"Avisos recientes:\n{avisos_str if avisos_str else 'No hay avisos recientes.'}\n\n"
                        f"Horario de clases:\n{horario_str if horario_str else 'Horario no configurado.'}\n\n"
                        f"Instrucciones: "
                        f"1. Ayuda con calidez y paciencia. "
                        f"2. Explica conceptos de forma clara y sencilla. "
                        f"3. Si hay tareas pendientes, recuérdalas con motivación. "
                        f"4. Usa ejemplos prácticos. "
                        f"5. NUNCA uses lenguaje negativo. "
                        f"6. Siempre cierra con una palabra de aliento."
                    )
                    
                    response = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[{"role": "system", "content": system_prompt}, *st.session_state.messages],
                        stream=True,
                    )
                    
                    full_response = ""
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            full_response += chunk.choices[0].delta.content
                    
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    guardar_mensaje(st.session_state.current_chat_id, "assistant", full_response)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
