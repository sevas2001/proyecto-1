import re
import yaml
from typing import Dict, Any, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
import os

class AgentClassifier:
    """
    Agente de clasificación.
    - Usa heurísticas (keywords + regex) como soporte inicial.
    - Usa LLM (GPT) para razonamiento profundo y detección de matices.
    """

    def __init__(self, policy_path: str):
        with open(policy_path, "r", encoding="utf-8") as f:
            self.policy = yaml.safe_load(f)

        load_dotenv()
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.output_parser = JsonOutputParser()
        
        self.prompt = ChatPromptTemplate.from_template(
            """
            Eres un experto en moderación de contenido para una red social similar a Instagram.
            Tu tarea es analizar el siguiente texto y clasificarlo según nuestra política.

            POLÍTICA DE CATEGORÍAS DISPONIBLES:
            {policy_categories}

            TEXTO A ANALIZAR:
            "{text}"

            INSTRUCCIONES:
            1. Identifica qué categorías de la política se violan (si ninguna, deja la lista vacía).
            2. Asigna un nivel de confianza (0.0 a 1.0) para la clasificación general.
            3. Enumera las señales o extractos de texto que justifican la decisión.

            RESPONDE ÚNICAMENTE EN FORMATO JSON con la siguiente estructura:
            {{
                "labels": ["categoria1", "categoria2"],
                "confidence": 0.95,
                "signals": ["frase ofensiva detectada", "intento de estafa"]
            }}
            """
        )

    def _heuristic_classification(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        labels: List[str] = []
        signals: List[str] = []
        score = 0.0

        for category, config in self.policy["categories"].items():
            # Keywords
            for kw in config.get("keywords", []):
                if kw.lower() in text_lower:
                    labels.append(category)
                    signals.append(f"keyword_{category}")
                    score += 0.2

            # Regex
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

    def classify(self, post: Dict[str, Any]) -> Dict[str, Any]:
        text = post.get("text", "")
        
        # 1. Obtener señales heurísticas (útil como contexto o fallback)
        heuristics = self._heuristic_classification(text)
        
        # 2. Razonamiento inteligente con LLM
        try:
            chain = self.prompt | self.llm | self.output_parser
            categories_str = ", ".join(self.policy["categories"].keys())
            
            ai_result = chain.invoke({
                "text": text,
                "policy_categories": categories_str
            })
            
            # Mezclamos señales para un trace completo
            ai_result["signals"] = list(set(ai_result.get("signals", []) + heuristics["signals"]))
            return ai_result
            
        except Exception as e:
            # Fallback a heurísticas si falla la API
            heuristics["signals"].append(f"llm_error: {str(e)}")
            return heuristics
