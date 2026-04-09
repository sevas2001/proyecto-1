"""
Test manual de la política de moderación.

Ejecutar con:
    python test_policy.py

No modifica arquitectura existente.
Usa el pipeline completo vía moderate_post.
"""

import sys
import os

# Añadimos el directorio "app" al PYTHONPATH para que
# los imports internos como "moderation.*" funcionen correctamente
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
APP_PATH = os.path.join(BASE_DIR, "app")
if APP_PATH not in sys.path:
    sys.path.append(APP_PATH)

from moderation.orchestrator import moderate_post


def run_test_case(post_id: str, text: str):
    post = {
        "id": post_id,
        "text": text
    }

    result = moderate_post(post)

    print("=" * 80)
    print(f"TEXTO: {text}")
    print(f"STATUS FINAL: {result['status']}")
    print(f"RAZÓN: {result['reason']}")
    print("TRACE:")
    for step in result["trace"]:
        print(f"  - {step['stage']}: {step['output']}")
    print("=" * 80)

    return result["status"]


def main():
    approved = 0
    rejected = 0
    review = 0

    test_cases = [

        # 1. Texto completamente limpio → debería APROBARSE
        ("1", "Hoy es un buen día para aprender algo nuevo y compartir conocimiento."),

        # 2. Spam obvio → debería RECHAZARSE
        ("2", "GANA DINERO AHORA 200% de ganancia asegurada! Haz clic aquí ahora mismo https://scam.com"),

        # 3. Spam camuflado con una URL → probablemente REVISION_HUMANA
        ("3", "Estoy probando una plataforma interesante, ¿alguien ha usado https://example.com antes?"),

        # 4. Odio explícito → debería RECHAZARSE
        ("4", "Esos son inferiores por naturaleza y deberían desaparecer."),

        # 5. Violencia real directa → debería RECHAZARSE
        ("5", "Voy a dispararte cuando te vea."),

        # 6. Amenaza directa → debería RECHAZARSE
        ("6", "Te voy a matar por lo que hiciste."),

        # 7. Uso contextual legítimo → debería APROBARSE
        ("7", "Esa película me mató de risa, fue increíble."),

        # 8. Datos personales (email) → REVISION_HUMANA
        ("8", "Contáctame en ejemplo123@gmail.com para más información."),

        # 9. Caso ambiguo → probablemente REVISION_HUMANA
        ("9", "Ese grupo es un problema para la sociedad."),

        # 10. Caso borderline agresivo sin amenaza real → REVISION_HUMANA
        ("10", "Te vas a arrepentir de esto algún día.")
    ]

    for post_id, text in test_cases:
        status = run_test_case(post_id, text)

        if status == "APROBADO":
            approved += 1
        elif status == "RECHAZADO":
            rejected += 1
        elif status == "REVISION_HUMANA":
            review += 1

    print("\n" + "=" * 40)
    print("RESUMEN FINAL")
    print("=" * 40)
    print(f"APROBADO: {approved}")
    print(f"RECHAZADO: {rejected}")
    print(f"REVISION_HUMANA: {review}")
    print("=" * 40)


if __name__ == "__main__":
    main()
