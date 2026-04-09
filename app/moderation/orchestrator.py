"""
STUB del módulo de moderación.
Este archivo será reemplazado por el equipo de moderación con la implementación real.

Contrato de la función:
    Entrada:  post (dict) con claves: id, text, image_path (puede ser None)
    Salida:   dict con:
                - status  (str): "APROBADO" | "RECHAZADO" | "REVISION_HUMANA"
                - reason  (str): explicación legible de la decisión
                - trace   (list[dict]): pasos internos del proceso de moderación

La app principal captura cualquier excepción de esta función y marca el post
como REVISION_HUMANA para que un humano lo revise manualmente.
"""


def moderate_post(post: dict) -> dict:
    """
    Stub de moderación. Aprueba todo por defecto.
    Reemplazar con la implementación real del equipo de moderación.
    """
    return {
        "status": "APROBADO",
        "reason": "Contenido aprobado automáticamente (módulo stub).",
        "trace": [
            {
                "step": "stub_inicializado",
                "resultado": "ok",
                "detalle": "Módulo de moderación pendiente de implementación real."
            },
            {
                "step": "decision_final",
                "resultado": "APROBADO",
                "detalle": f"Post id={post.get('id', 'desconocido')} aprobado sin filtros."
            }
        ]
    }
