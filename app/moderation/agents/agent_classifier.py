import re
import yaml
import base64
from typing import Dict, Any, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
import os


class AgentClassifier:
    """
    Agente de clasificación multimodal.
    Compatible con el sistema actual (NO rompe orchestrator).
    
    Soporta:
    - Texto
    - Imagen
    - Texto + Imagen (multimodal GPT-4o)
    
    Mantiene EXACTAMENTE el mismo formato de salida:
    {
        "labels": [...],
        "confidence": float,
        "signals": [...]
    }
    """

    def __init__(self, policy_path: str):
        with open(policy_path, "r", encoding="utf-8") as f:
            self.policy = yaml.safe_load(f)

        load_dotenv()

        self.llm = ChatOpenAI(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            base_url=f"{os.getenv('AZURE_OPENAI_ENDPOINT')}/v1",
            temperature=0
        )

        self.output_parser = JsonOutputParser()

        # Prompt solo texto (comportamiento original)
        self.prompt = ChatPromptTemplate.from_template(
            """
            Eres un experto en moderación de contenido para una red social similar a Instagram.
            Tu tarea es analizar el siguiente texto y clasificarlo según nuestra política.

            POLÍTICA DE CATEGORÍAS DISPONIBLES:
            {policy_categories}

            TEXTO A ANALIZAR:
            "{text}"

            RESPONDE ÚNICAMENTE EN FORMATO JSON con la siguiente estructura:
            {{
                "labels": ["categoria1"],
                "confidence": 0.95,
                "signals": ["razón concreta"]
            }}
            """
        )

    # ------------------------------------------------------------------
    # HEURÍSTICA LOCAL (NO SE MODIFICA)
    # ------------------------------------------------------------------

    def _heuristic_classification(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        labels: List[str] = []
        signals: List[str] = []
        score = 0.0

        for category, config in self.policy["categories"].items():
            for kw in config.get("keywords", []):
                if kw.lower() in text_lower:
                    labels.append(category)
                    signals.append(f"keyword_{category}")
                    score += 0.2

            for pattern in config.get("regex", []):
                if re.search(pattern, text, re.IGNORECASE):
                    labels.append(category)
                    signals.append(f"regex_{category}")
                    score += 0.3

        return {
            "labels": list(set(labels)),
            "confidence": min(score, 1.0),
            "signals": signals
        }

    # ------------------------------------------------------------------
    # NUEVO: ANALISIS MULTIMODAL
    # ------------------------------------------------------------------

    def _encode_image_base64(self, image_path: str) -> str:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")

    def _analyze_multimodal(self, text: str, image_path: str) -> Dict[str, Any]:
        """
        Analiza texto + imagen en una sola request GPT‑4o.
        """
        categories_str = ", ".join(self.policy["categories"].keys())

        image_b64 = self._encode_image_base64(image_path)

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""
                        Eres un experto en moderación de contenido.

                        POLÍTICA:
                        {categories_str}

                        Analiza el texto y la imagen conjuntamente.
                        Devuelve JSON con:
                        {{
                            "labels": [],
                            "confidence": 0.0,
                            "signals": []
                        }}

                        TEXTO:
                        {text}
                        """
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ]

        response = self.llm.invoke(messages)

        return self.output_parser.invoke(response)

    # ------------------------------------------------------------------
    # CLASIFICACIÓN PRINCIPAL
    # ------------------------------------------------------------------

    def classify(self, post: Dict[str, Any]) -> Dict[str, Any]:
        text = post.get("text", "") or ""
        image_path = post.get("image_path")

        # Validación estricta: solo procesar imagen si existe físicamente
        if image_path and not os.path.exists(image_path):
            image_path = None

        heuristics = self._heuristic_classification(text)
        input_type = "text"

        try:
            # CASO 1: Texto + Imagen
            if text and image_path:
                try:
                    ai_result = self._analyze_multimodal(text, image_path)
                    input_type = "multimodal"
                except Exception as img_error:
                    # Fallback a texto si falla imagen
                    input_type = "text_fallback"
                    chain = self.prompt | self.llm | self.output_parser
                    categories_str = ", ".join(self.policy["categories"].keys())
                    ai_result = chain.invoke({
                        "text": text,
                        "policy_categories": categories_str
                    })

            # CASO 2: Solo imagen
            elif image_path and not text:
                try:
                    ai_result = self._analyze_multimodal("", image_path)
                    input_type = "image"
                except Exception as img_error:
                    return {
                        "labels": [],
                        "confidence": 0.0,
                        "signals": [f"image_error: {str(img_error)}"]
                    }

            # CASO 3: Solo texto
            else:
                chain = self.prompt | self.llm | self.output_parser
                categories_str = ", ".join(self.policy["categories"].keys())
                ai_result = chain.invoke({
                    "text": text,
                    "policy_categories": categories_str
                })
                input_type = "text"

            # Fusionar señales heurísticas
            ai_result["signals"] = list(
                set(ai_result.get("signals", []) + heuristics["signals"])
            )

            # Añadir metadatos al trace sin romper formato
            ai_result["signals"].append(f"input_type:{input_type}")

            return ai_result

        except Exception as e:
            heuristics["signals"].append(f"llm_error: {str(e)}")
            heuristics["signals"].append(f"input_type:{input_type}")
            return heuristics
