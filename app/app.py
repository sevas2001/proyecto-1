"""
ModerApp — Instagram simplificado con:

✅ Moderación automática + humana
✅ Autenticación
✅ Roles (admin / user)
✅ Sistema de reputación
✅ Baneo automático
✅ Feed filtrado
✅ Mis Posts
"""

import os
import sys
import uuid
import sqlite3
import hashlib
import logging
from datetime import datetime, timezone

import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------
# PATH CONFIG
# ---------------------------------------------------------------------

APP_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(APP_DIR)

if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from storage.storage import load_posts, save_posts as storage_save_posts, add_post, update_post, IMAGES_DIR
from moderation.orchestrator import moderate_post

# ---------------------------------------------------------------------
# CONSTANTES ORIGINALES
# ---------------------------------------------------------------------

MAX_TEXTO = 1000
MAX_IMAGEN_MB = 5
MAX_IMAGEN_BYTES = MAX_IMAGEN_MB * 1024 * 1024

ESTADO_EMOJI = {
    "APROBADO": "🟢",
    "RECHAZADO": "🔴",
    "REVISION_HUMANA": "🟡",
    "PENDIENTE": "⚪",
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------
# DATABASE CONFIG
# ---------------------------------------------------------------------

DB_PATH = os.path.join(ROOT_DIR, "users.db")


def create_users_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,
            approved_count INTEGER DEFAULT 0,
            rejected_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'normal'
        )
    """)
    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(username, password, role="user"):
    """
    Registro de usuario con validación de contraseña por rol.
    - admin: sin mínimo de caracteres
    - user: mínimo 6 caracteres
    """
    if role == "user" and len(password) < 6:
        return False, "La contraseña debe tener al menos 6 caracteres."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO users (username, password_hash, role, approved_count, rejected_count, status)
            VALUES (?, ?, ?, 0, 0, 'normal')
        """, (username, hash_password(password), role))
        conn.commit()
        return True, "Usuario registrado correctamente."
    except sqlite3.IntegrityError:
        return False, "El usuario ya existe."
    finally:
        conn.close()


def login_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, password_hash, role, status FROM users WHERE username=?", (username,))
    user = c.fetchone()
    conn.close()

    if not user:
        return False, "Usuario no encontrado."

    if user[3] == "baneado":
        return False, "Cuenta bloqueada por reiteradas infracciones."

    if hash_password(password) == user[1]:
        return True, {"username": user[0], "role": user[2], "status": user[3]}
    return False, "Contraseña incorrecta."


def update_user_stats(username, post_status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    if post_status == "APROBADO":
        c.execute("UPDATE users SET approved_count = approved_count + 1 WHERE username=?", (username,))
    elif post_status == "RECHAZADO":
        c.execute("UPDATE users SET rejected_count = rejected_count + 1 WHERE username=?", (username,))

    conn.commit()
    conn.close()
    update_user_status(username)


def update_user_status(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT rejected_count FROM users WHERE username=?", (username,))
    rejected = c.fetchone()[0]

    new_status = "normal"
    if rejected >= 11:
        new_status = "baneado"
    elif rejected == 10:
        new_status = "advertencia_final"
    elif rejected >= 5:
        new_status = "alerta"

    c.execute("UPDATE users SET status=? WHERE username=?", (new_status, username))
    conn.commit()
    conn.close()


def get_user_info(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT approved_count, rejected_count, status FROM users WHERE username=?", (username,))
    data = c.fetchone()
    conn.close()
    return data


# ---------------------------------------------------------------------
# HELPERS ORIGINALES
# ---------------------------------------------------------------------

def generar_id():
    return str(uuid.uuid4())


def generar_timestamp():
    return datetime.now(timezone.utc).isoformat()


def guardar_imagen(uploaded_file):
    extension = os.path.splitext(uploaded_file.name)[1].lower()
    nombre = f"{generar_id()}{extension}"
    ruta = os.path.join(IMAGES_DIR, nombre)
    with open(ruta, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return nombre


def ruta_imagen(nombre_archivo):
    return os.path.join(IMAGES_DIR, nombre_archivo)


def publicar_post(user, text, imagen_file=None):

    image_filename = None
    if imagen_file:
        image_filename = guardar_imagen(imagen_file)

    post = {
        "id": generar_id(),
        "user": user,
        "text": text,
        "image_path": image_filename,
        "created_at": generar_timestamp(),
        "status": "PENDIENTE",
        "moderation_reason": None,
        "trace": [],
        "human_review": None,
    }

    imagen_abs = ruta_imagen(image_filename) if image_filename else None

    resultado = moderate_post({
        "id": post["id"],
        "text": post["text"],
        "image_path": imagen_abs,
    })

    post["status"] = resultado.get("status")
    post["moderation_reason"] = resultado.get("reason")
    post["trace"] = resultado.get("trace")

    add_post(post)

    # actualizar reputación
    if st.session_state.authenticated:
        update_user_stats(user, post["status"])

    return post


# ---------------------------------------------------------------------
# SESSION INIT
# ---------------------------------------------------------------------

create_users_table()

def initialize_default_admins():
    """
    Inserta los admins por defecto SOLO si la tabla está vacía.
    No borra usuarios existentes.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]

    if count == 0:
        admins = [
            ("raul", "1234"),
            ("sevas", "1234"),
        ]

        for username, password in admins:
            c.execute("""
                INSERT INTO users (username, password_hash, role, approved_count, rejected_count, status)
                VALUES (?, ?, 'admin', 0, 0, 'normal')
            """, (username, hash_password(password)))

        conn.commit()

    conn.close()

# Inicializar admins solo si la tabla está vacía
initialize_default_admins()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.user_status = None

# ---------------------------------------------------------------------
# ADMIN HELPERS
# ---------------------------------------------------------------------

def is_admin():
    """Verifica si el usuario actual es administrador."""
    return (
        st.session_state.get("authenticated")
        and st.session_state.get("role") == "admin"
    )


# ---------------------------------------------------------------------
# HUMAN REVIEW CORE FUNCTIONS
# ---------------------------------------------------------------------

def save_posts(posts: dict):
    """
    Reescribe completamente el archivo de posts de forma segura.
    """
    return storage_save_posts(posts)


def get_pending_posts():
    """
    Devuelve únicamente posts en revisión humana.
    Soporta variantes como:
    - REVISION_HUMANA
    - REQUIERE_REVISIÓN_HUMANA
    """
    posts = load_posts()

    pending = {}

    for pid, p in posts.items():
        status = str(p.get("status", "")).strip().upper()

        if (
            status == "REVISION_HUMANA"
            or "REVISION" in status and "HUMANA" in status
            or "REQUIERE" in status and "HUMANA" in status
        ):
            # Normalizar estado internamente
            p["status"] = "REVISION_HUMANA"
            pending[pid] = p

    return pending


def apply_admin_decision(post_id, decision, justification, admin_username):
    """
    Aplica decisión manual del admin sin duplicar posts
    ni perder información previa.
    """
    posts = load_posts()

    if post_id not in posts:
        return False, "Post no encontrado."

    post = posts[post_id]

    current_status = str(post.get("status", "")).upper()

    if not (
        current_status == "REVISION_HUMANA"
        or "REVISION" in current_status and "HUMANA" in current_status
        or "REQUIERE" in current_status and "HUMANA" in current_status
    ):
        return False, "El post ya fue procesado."

    post["status"] = decision
    post["moderation_reason"] = "Decisión manual del administrador"

    post["admin_decision"] = {
        "admin_username": admin_username,
        "decision": decision,
        "justificacion": justification,
        "timestamp": generar_timestamp()
    }

    posts[post_id] = post

    ok = save_posts(posts)
    if not ok:
        return False, "Error al guardar cambios."

    update_user_stats(post["user"], decision)

    return True, "Decisión aplicada correctamente."


def render_auditoria():
    """Panel de auditoría completo (solo admin)."""

    if not is_admin():
        st.error("Acceso restringido a administradores.")
        return

    st.subheader("📋 Panel de Auditoría")

    posts = load_posts()

    if not posts:
        st.info("No hay posts registrados.")
        return

    for post in sorted(posts.values(), key=lambda x: x["created_at"], reverse=True):
        with st.expander(f"Post {post['id']} - @{post['user']}"):

            st.markdown(f"**Usuario:** @{post['user']}")
            st.markdown(f"**Texto:** {post['text']}")
            st.markdown(f"**Estado final:** {post['status']}")
            st.markdown(f"**Razón final:** {post.get('moderation_reason')}")

            st.markdown("### 🔎 Trace completo")
            for step in post.get("trace", []):
                st.json(step)

            if post.get("admin_decision"):
                st.markdown("### 👮 Decisión Administrador")
                st.json(post["admin_decision"])


def render_moderacion_admin():
    """Panel de moderación manual (solo admin)."""

    if not is_admin():
        st.error("Acceso restringido a administradores.")
        return

    st.subheader("🛡️ Moderación Humana")

    pendientes = get_pending_posts()

    if not pendientes:
        st.success("No hay posts pendientes de revisión.")
        return

    for post_id, post in pendientes.items():

        st.markdown("---")
        st.markdown(f"### 👤 Usuario: @{post['user']}")
        st.markdown(f"**Texto:** {post['text']}")

        if post.get("image_path"):
            ruta = ruta_imagen(post["image_path"])
            if os.path.exists(ruta):
                st.image(ruta, use_container_width=True)

        st.markdown(f"**Motivo actual:** {post.get('moderation_reason')}")

        st.markdown("### 🔎 Trace de agentes")
        for step in post.get("trace", []):
            st.json(step)

        justificacion = st.text_area(
            "Justificación del administrador (obligatoria)",
            key=f"just_{post_id}"
        )

        col1, col2 = st.columns(2)

        with col1:
            aprobar = st.button("✅ Aprobar", key=f"aprobar_{post_id}")

        with col2:
            rechazar = st.button("❌ Rechazar", key=f"rechazar_{post_id}")

        if aprobar or rechazar:

            if not justificacion.strip():
                st.error("La justificación es obligatoria.")
                st.stop()

            decision = "APROBADO" if aprobar else "RECHAZADO"

            ok, msg = apply_admin_decision(
                post_id,
                decision,
                justificacion,
                st.session_state.username
            )

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)


# ---------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------

st.set_page_config(page_title="ModerApp", page_icon="📸", layout="wide")
st.title("📸 ModerApp")

tabs = ["✏️ Crear post", "🖼️ Feed"]

if st.session_state.authenticated:
    tabs.append("📂 Mis Posts")

if st.session_state.role == "admin":
    tabs.extend(["🛡️ Moderación", "📋 Auditoría"])

tabs.append("🔐 Autenticación")

tab_objs = st.tabs(tabs)

# ---------------------------------------------------------------------
# TAB CREAR POST
# ---------------------------------------------------------------------

with tab_objs[0]:

    if not st.session_state.authenticated:
        st.warning("Debes iniciar sesión para publicar.")
    else:
        with st.form("crear_post", clear_on_submit=True):
            texto = st.text_area("Texto", max_chars=MAX_TEXTO)
            imagen = st.file_uploader("Imagen opcional", type=["jpg", "png", "jpeg"])
            enviar = st.form_submit_button("Publicar")

        if enviar and texto.strip():
            post = publicar_post(st.session_state.username, texto, imagen)
            emoji = ESTADO_EMOJI.get(post["status"], "⚪")
            st.success(f"Estado: {emoji} {post['status']}")
            st.info(post["moderation_reason"])

# ---------------------------------------------------------------------
# TAB FEED
# ---------------------------------------------------------------------

with tab_objs[1]:

    posts = load_posts()
    aprobados = [
        p for p in posts.values()
        if p["status"] == "APROBADO"
        and p["user"] != st.session_state.username
    ]

    for post in sorted(aprobados, key=lambda x: x["created_at"], reverse=True):
        st.markdown(f"**@{post['user']}**")
        st.write(post["text"])

# ---------------------------------------------------------------------
# TAB MIS POSTS
# ---------------------------------------------------------------------

if st.session_state.authenticated:
    with tab_objs[2]:
        posts = load_posts()
        propios = [p for p in posts.values() if p["user"] == st.session_state.username]

        approved, rejected, status = get_user_info(st.session_state.username)
        st.write(f"Aprobados: {approved} | Rechazados: {rejected} | Estado: {status}")

        for p in propios:
            st.markdown(f"**{p['status']}** - {p['text']}")

# ---------------------------------------------------------------------
# TAB MODERACIÓN (ADMIN)
# ---------------------------------------------------------------------

if is_admin():
    with tab_objs[-3]:
        render_moderacion_admin()

# ---------------------------------------------------------------------
# TAB AUDITORÍA (ADMIN)
# ---------------------------------------------------------------------

if is_admin():
    with tab_objs[-2]:
        render_auditoria()

# ---------------------------------------------------------------------
# TAB AUTENTICACIÓN
# ---------------------------------------------------------------------

with tab_objs[-1]:

    if not st.session_state.authenticated:

        modo = st.radio("Modo", ["Login", "Registro"])
        user = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")

        if modo == "Registro":
            if st.button("Crear cuenta"):
                ok, msg = register_user(user, pwd)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)
        else:
            if st.button("Iniciar sesión"):
                ok, result = login_user(user, pwd)
                if ok:
                    st.session_state.authenticated = True
                    st.session_state.username = result["username"]
                    st.session_state.role = result["role"]
                    st.session_state.user_status = result["status"]
                    st.rerun()
                else:
                    st.error(result)

    else:
        st.success(f"Sesión activa: @{st.session_state.username}")
        if st.button("Cerrar sesión"):
            st.session_state.authenticated = False
            st.rerun()
