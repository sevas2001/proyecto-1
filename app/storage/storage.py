"""
Módulo de persistencia: lectura y escritura de posts en JSON.
Formato de almacenamiento: dict indexado por id de post.
{
    "uuid-1": { "id": "uuid-1", "user": ..., "text": ..., ... },
    "uuid-2": { ... }
}
"""
import json
import os
import logging

# Rutas absolutas basadas en la ubicación de este archivo
STORAGE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_FILE = os.path.join(STORAGE_DIR, "posts.json")
IMAGES_DIR = os.path.join(STORAGE_DIR, "uploaded_images")

logger = logging.getLogger(__name__)


def _asegurar_directorios():
    """Crea los directorios necesarios si no existen."""
    os.makedirs(IMAGES_DIR, exist_ok=True)


def load_posts() -> dict:
    """
    Carga todos los posts desde el archivo JSON.
    Retorna un dict vacío si el archivo no existe o está corrupto.
    """
    _asegurar_directorios()
    if not os.path.exists(POSTS_FILE):
        return {}
    try:
        with open(POSTS_FILE, "r", encoding="utf-8") as f:
            contenido = f.read().strip()
            if not contenido:
                return {}
            return json.loads(contenido)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error al leer posts.json: {e}")
        return {}


def save_posts(posts: dict) -> bool:
    """
    Guarda el dict completo de posts en el archivo JSON.
    Retorna True si tuvo éxito, False si hubo error.
    """
    _asegurar_directorios()
    try:
        # Escritura atómica: primero a un archivo temporal, luego rename
        ruta_tmp = POSTS_FILE + ".tmp"
        with open(ruta_tmp, "w", encoding="utf-8") as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
        os.replace(ruta_tmp, POSTS_FILE)
        return True
    except IOError as e:
        logger.error(f"Error al guardar posts.json: {e}")
        return False


def add_post(post: dict) -> bool:
    """
    Agrega un post nuevo al almacenamiento.
    Retorna True si se guardó correctamente.
    """
    posts = load_posts()
    posts[post["id"]] = post
    return save_posts(posts)


def update_post(post_id: str, fields: dict) -> bool:
    """
    Actualiza campos específicos de un post existente.
    Retorna True si el post existía y se actualizó.
    """
    posts = load_posts()
    if post_id not in posts:
        logger.warning(f"update_post: id '{post_id}' no encontrado.")
        return False
    posts[post_id].update(fields)
    return save_posts(posts)
