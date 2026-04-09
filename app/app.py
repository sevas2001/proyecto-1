"""
ModerApp — Demo "Instagram simplificado" con moderación de contenido asistida por IA.

Navegación:
  - Crear post   : publicar texto + imagen opcional (pasa por moderación automática)
  - Feed         : ver solo posts con estado APROBADO
  - Moderación   : cola de revisión humana (REVISION_HUMANA)
  - Auditoría    : historial completo con trace de cada post

Ejecutar:
    streamlit run app/app.py
"""

import os
import sys
import uuid
import logging
from datetime import datetime, timezone

import streamlit as st
from PIL import Image

# ---------------------------------------------------------------------------
# Configurar path para importar módulos del mismo paquete
# ---------------------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from storage.storage import load_posts, add_post, update_post, IMAGES_DIR
from moderation.orchestrator import moderate_post

# ---------------------------------------------------------------------------
# Constantes de configuración
# ---------------------------------------------------------------------------
MAX_TEXTO = 1000          # Caracteres máximos por post
MAX_IMAGEN_MB = 5         # Tamaño máximo de imagen en MB
MAX_IMAGEN_BYTES = MAX_IMAGEN_MB * 1024 * 1024
ESTADOS_VALIDOS = ["PENDIENTE", "APROBADO", "RECHAZADO", "REVISION_HUMANA"]

ESTADO_EMOJI = {
    "APROBADO":        "🟢",
    "RECHAZADO":       "🔴",
    "REVISION_HUMANA": "🟡",
    "PENDIENTE":       "⚪",
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers de utilidad
# ---------------------------------------------------------------------------

def generar_id() -> str:
    """Genera un UUID v4 como string."""
    return str(uuid.uuid4())


def generar_timestamp() -> str:
    """Retorna la fecha/hora actual en formato ISO 8601 UTC."""
    return datetime.now(timezone.utc).isoformat()


def guardar_imagen(uploaded_file) -> str:
    """
    Guarda el archivo subido en uploaded_images/ con nombre único.
    Retorna el nombre del archivo (no la ruta completa).
    """
    extension = os.path.splitext(uploaded_file.name)[1].lower()
    nombre = f"{generar_id()}{extension}"
    ruta = os.path.join(IMAGES_DIR, nombre)
    with open(ruta, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return nombre


def ruta_imagen(nombre_archivo: str) -> str:
    """Devuelve la ruta absoluta de una imagen dado su nombre de archivo."""
    return os.path.join(IMAGES_DIR, nombre_archivo)


# ---------------------------------------------------------------------------
# Lógica de negocio
# ---------------------------------------------------------------------------

def publicar_post(user: str, text: str, imagen_file=None) -> dict:
    """
    Flujo completo de publicación:
      1. Guarda imagen (si existe)
      2. Crea el post con estado PENDIENTE
      3. Llama a moderate_post (captura excepciones)
      4. Actualiza el post con el resultado de moderación
      5. Persiste en JSON
    Retorna el post final ya persistido.
    """
    # 1. Guardar imagen
    image_filename = None
    if imagen_file is not None:
        try:
            image_filename = guardar_imagen(imagen_file)
        except IOError as e:
            logger.error(f"No se pudo guardar la imagen: {e}")
            # Continuar sin imagen antes que romper el flujo

    # 2. Construir post inicial
    post = {
        "id":                generar_id(),
        "user":              user,
        "text":              text,
        "image_path":        image_filename,
        "created_at":        generar_timestamp(),
        "status":            "PENDIENTE",
        "moderation_reason": None,
        "trace":             [],
        "human_review":      None,
    }

    # 3. Llamar al módulo de moderación
    imagen_abs = ruta_imagen(image_filename) if image_filename else None
    try:
        resultado = moderate_post({
            "id":         post["id"],
            "text":       post["text"],
            "image_path": imagen_abs,
        })
        post["status"]            = resultado.get("status", "REVISION_HUMANA")
        post["moderation_reason"] = resultado.get("reason", "")
        post["trace"]             = resultado.get("trace", [])
    except Exception as e:
        # Si la moderación falla, el post queda para revisión humana
        mensaje_error = f"Error inesperado en moderate_post: {str(e)}"
        logger.error(mensaje_error)
        post["status"]            = "REVISION_HUMANA"
        post["moderation_reason"] = mensaje_error
        post["trace"]             = [{"step": "error_capturado", "detalle": str(e)}]

    # 4. Persistir
    add_post(post)
    return post


def aprobar_post(post_id: str, motivo: str):
    """Decisión humana: aprobar un post en REVISION_HUMANA."""
    human_review = {
        "reviewer":  "moderador",
        "decision":  "APROBADO",
        "reason":    motivo,
        "timestamp": generar_timestamp(),
    }
    update_post(post_id, {"status": "APROBADO", "human_review": human_review})


def rechazar_post(post_id: str, motivo: str):
    """Decisión humana: rechazar un post en REVISION_HUMANA."""
    human_review = {
        "reviewer":  "moderador",
        "decision":  "RECHAZADO",
        "reason":    motivo,
        "timestamp": generar_timestamp(),
    }
    update_post(post_id, {"status": "RECHAZADO", "human_review": human_review})


# ---------------------------------------------------------------------------
# UI — Configuración global de Streamlit
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="ModerApp",
    page_icon="📸",
    layout="wide",
)

st.title("📸 ModerApp — Instagram simplificado con Moderación IA")
st.caption("Demo MVP · Persistencia local JSON · Moderación automática + revisión humana")
st.divider()

tab_crear, tab_feed, tab_mod, tab_audit = st.tabs([
    "✏️ Crear post",
    "🖼️ Feed",
    "🛡️ Moderación",
    "📋 Auditoría",
])


# ===========================================================================
# TAB 1 — CREAR POST
# ===========================================================================

with tab_crear:
    st.header("Nuevo post")

    with st.form("form_crear_post", clear_on_submit=True):
        usuario = st.text_input(
            "Usuario",
            value="usuario_demo",
            max_chars=50,
            help="Nombre de usuario (sin @)",
        )

        texto = st.text_area(
            "Texto del post *",
            max_chars=MAX_TEXTO,
            height=150,
            placeholder="¿Qué está pasando?",
        )

        # Imagen opcional
        imagen_file = st.file_uploader(
            f"Imagen opcional (JPG / PNG · máx. {MAX_IMAGEN_MB} MB)",
            type=["jpg", "jpeg", "png"],
        )

        enviado = st.form_submit_button("Publicar", type="primary", use_container_width=True)

    # Contador de caracteres (fuera del form para actualización reactiva)
    chars = len(texto) if "texto" in dir() else 0

    # Validaciones y publicación
    if enviado:
        errores = []

        if not usuario.strip():
            errores.append("El nombre de usuario no puede estar vacío.")
        if not texto.strip():
            errores.append("El texto del post es obligatorio.")
        if imagen_file is not None and imagen_file.size > MAX_IMAGEN_BYTES:
            errores.append(f"La imagen supera el límite de {MAX_IMAGEN_MB} MB "
                           f"({imagen_file.size / 1024 / 1024:.1f} MB).")

        if errores:
            for err in errores:
                st.error(err)
        else:
            # Vista previa de imagen antes de subir
            if imagen_file is not None:
                try:
                    preview = Image.open(imagen_file)
                    st.image(preview, caption="Vista previa", width=300)
                    imagen_file.seek(0)  # Resetear puntero tras leer para PIL
                except Exception:
                    pass

            with st.spinner("Enviando a moderación..."):
                post_creado = publicar_post(
                    user=usuario.strip(),
                    text=texto.strip(),
                    imagen_file=imagen_file,
                )

            emoji = ESTADO_EMOJI.get(post_creado["status"], "⚪")
            st.success(f"Post publicado · ID: `{post_creado['id']}`")
            st.info(
                f"Estado tras moderación: {emoji} **{post_creado['status']}**  \n"
                f"Razón: {post_creado.get('moderation_reason') or '—'}"
            )


# ===========================================================================
# TAB 2 — FEED
# ===========================================================================

with tab_feed:
    st.header("Feed público")
    st.caption("Solo se muestran posts con estado APROBADO · orden cronológico inverso")

    posts = load_posts()
    aprobados = sorted(
        [p for p in posts.values() if p["status"] == "APROBADO"],
        key=lambda p: p["created_at"],
        reverse=True,
    )

    if not aprobados:
        st.info("No hay posts aprobados todavía. ¡Crea el primero!")
    else:
        for post in aprobados:
            with st.container(border=True):
                col_texto, col_img = st.columns([3, 1])

                with col_texto:
                    fecha = post["created_at"][:10]
                    hora  = post["created_at"][11:16]
                    st.markdown(f"**@{post['user']}** · {fecha} {hora} UTC")
                    st.write(post["text"])

                with col_img:
                    if post.get("image_path"):
                        ruta = ruta_imagen(post["image_path"])
                        if os.path.exists(ruta):
                            st.image(ruta, use_container_width=True)


# ===========================================================================
# TAB 3 — MODERACIÓN
# ===========================================================================

with tab_mod:
    st.header("Panel de moderación")
    st.caption("Cola de posts en REVISION_HUMANA · toma decisiones manuales")

    posts = load_posts()
    en_revision = sorted(
        [p for p in posts.values() if p["status"] == "REVISION_HUMANA"],
        key=lambda p: p["created_at"],
    )

    if not en_revision:
        st.success("✅ Cola vacía — no hay posts pendientes de revisión humana.")
    else:
        st.warning(f"**{len(en_revision)}** post(s) esperando revisión.")

        # Selector de post
        opciones_labels = [
            f"@{p['user']} · {p['created_at'][:10]} · id={p['id'][:8]}…"
            for p in en_revision
        ]
        idx = st.selectbox("Seleccionar post", range(len(en_revision)),
                           format_func=lambda i: opciones_labels[i])

        post = en_revision[idx]

        st.divider()

        # Detalle del post seleccionado
        col_meta, col_media = st.columns([2, 1])

        with col_meta:
            st.markdown(f"**ID completo:** `{post['id']}`")
            st.markdown(f"**Usuario:** @{post['user']}")
            st.markdown(f"**Fecha:** {post['created_at']}")
            st.markdown(f"**Razón de derivación IA:** {post.get('moderation_reason') or '—'}")
            st.markdown("**Texto del post:**")
            st.info(post["text"])

        with col_media:
            if post.get("image_path"):
                ruta = ruta_imagen(post["image_path"])
                if os.path.exists(ruta):
                    st.image(ruta, caption="Imagen adjunta", use_container_width=True)
                else:
                    st.caption("⚠️ Imagen no encontrada en disco.")

        # Trace expandible
        with st.expander("📋 Trace de moderación IA (JSON)"):
            trace = post.get("trace", [])
            if trace:
                st.json(trace)
            else:
                st.caption("Sin trace disponible.")

        st.divider()

        # Formulario de decisión
        st.subheader("Decisión del moderador")
        motivo_mod = st.text_area(
            "Motivo (obligatorio para aprobar o rechazar)",
            key=f"motivo_{post['id']}",
            placeholder="Indica la razón de tu decisión...",
        )

        col_apr, col_rec = st.columns(2)

        with col_apr:
            if st.button("✅ Aprobar", key=f"apr_{post['id']}", type="primary",
                         use_container_width=True):
                if not motivo_mod.strip():
                    st.error("Debes ingresar un motivo antes de aprobar.")
                else:
                    aprobar_post(post["id"], motivo_mod.strip())
                    st.success("Post aprobado correctamente.")
                    st.rerun()

        with col_rec:
            if st.button("❌ Rechazar", key=f"rec_{post['id']}",
                         use_container_width=True):
                if not motivo_mod.strip():
                    st.error("Debes ingresar un motivo antes de rechazar.")
                else:
                    rechazar_post(post["id"], motivo_mod.strip())
                    st.warning("Post rechazado.")
                    st.rerun()


# ===========================================================================
# TAB 4 — AUDITORÍA
# ===========================================================================

with tab_audit:
    st.header("Auditoría completa")
    st.caption("Todos los posts con su estado, trace y revisión humana")

    posts = load_posts()
    todos = sorted(posts.values(), key=lambda p: p["created_at"], reverse=True)

    if not todos:
        st.info("No hay posts registrados aún.")
    else:
        # Filtros
        col_f1, col_f2 = st.columns([2, 1])
        with col_f1:
            filtro_estados = st.multiselect(
                "Filtrar por estado",
                ESTADOS_VALIDOS,
                default=ESTADOS_VALIDOS,
            )
        with col_f2:
            filtro_usuario = st.text_input("Filtrar por usuario", placeholder="todos")

        filtrados = [
            p for p in todos
            if p["status"] in filtro_estados
            and (not filtro_usuario or filtro_usuario.lower() in p["user"].lower())
        ]

        st.caption(f"Mostrando **{len(filtrados)}** de **{len(todos)}** posts")
        st.divider()

        for post in filtrados:
            emoji = ESTADO_EMOJI.get(post["status"], "⚪")
            label = (
                f"{emoji} [{post['status']}] "
                f"@{post['user']} · "
                f"{post['created_at'][:10]} · "
                f"id={post['id'][:8]}…"
            )
            with st.expander(label):
                # Texto truncado en lista, completo al expandir
                st.markdown(f"**Texto:** {post['text']}")
                st.markdown(f"**Imagen:** `{post.get('image_path') or 'ninguna'}`")
                st.markdown(
                    f"**Razón moderación IA:** {post.get('moderation_reason') or '—'}"
                )

                if post.get("trace"):
                    st.markdown("**Trace IA:**")
                    st.json(post["trace"])

                if post.get("human_review"):
                    st.markdown("**Revisión humana:**")
                    hr = post["human_review"]
                    st.markdown(
                        f"- Revisor: `{hr.get('reviewer')}`  \n"
                        f"- Decisión: `{hr.get('decision')}`  \n"
                        f"- Motivo: {hr.get('reason')}  \n"
                        f"- Timestamp: `{hr.get('timestamp')}`"
                    )
