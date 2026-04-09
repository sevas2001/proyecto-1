# ModerApp — Demo Instagram + Moderación IA

MVP de red social simplificada con moderación de contenido asistida por IA.

## Requisitos

- Python 3.9+
- pip

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecutar

```bash
streamlit run app/app.py
```

La app abre en `http://localhost:8501`.

## Estructura

```
proyecto-1/
├── app/
│   ├── app.py                        # Aplicación Streamlit principal
│   ├── moderation/
│   │   └── orchestrator.py           # STUB — reemplazar con implementación real
│   └── storage/
│       ├── storage.py                # Helpers de persistencia (JSON)
│       ├── posts.json                # Creado automáticamente al primer post
│       └── uploaded_images/          # Imágenes subidas (UUID + extensión)
├── requirements.txt
└── README.md
```

## Integrar el módulo de moderación real

Edita `app/moderation/orchestrator.py` y reemplaza el cuerpo de `moderate_post`.  
La función debe respetar este contrato:

```python
def moderate_post(post: dict) -> dict:
    # post contiene: id, text, image_path (str o None)
    return {
        "status": "APROBADO",          # | "RECHAZADO" | "REVISION_HUMANA"
        "reason": "Motivo legible",
        "trace":  [{"step": "...", "resultado": "..."}]
    }
```

Si la función lanza cualquier excepción, la app la captura automáticamente  
y marca el post como `REVISION_HUMANA` para revisión manual.

## Estados de un post

| Estado            | Descripción                                       |
|-------------------|---------------------------------------------------|
| `PENDIENTE`       | Recién creado, antes de moderar (transitorio)     |
| `APROBADO`        | Visible en el Feed público                        |
| `RECHAZADO`       | No visible; registrado con motivo                 |
| `REVISION_HUMANA` | Cola para moderador humano (panel Moderación)     |

## Límites configurables (en `app/app.py`)

| Constante       | Valor por defecto |
|-----------------|-------------------|
| `MAX_TEXTO`     | 1000 caracteres   |
| `MAX_IMAGEN_MB` | 5 MB              |
