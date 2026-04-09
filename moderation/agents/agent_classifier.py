import re
import yaml
from typing import Dict, Any, List

from langchain.prompts import ChatPromptTemplate


class AgentClassifier:
    """
    Agente de clasificación.
    - Usa heurísticas (keywords + regex)
    - Preparado para integrar LLM con LangChain
    """

    def __init__(self, policy_path: str):
        with open(policy_path, "r", encoding="utf-8") as f:
            self.policy = yaml.safe_load(f)

        # Prompt preparado para futura integración LLM
        self.prompt = ChatPromptTemplate.from_template(
            """
            Analiza el siguiente texto y clasifícalo en categorías de moderación:
            {text}

            Devuelve categorías relevantes.
            """
        )

        # ⚠️ LLM opcional (no activado por defecto)
        self.llm = None  # Aquí podrías usar ChatOpenAI()

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

        confidence = min(score, 1.0)

        return {
            "labels": list(set(labels)),
            "confidence": round(confidence, 2),
            "signals": signals
        }

    def classify(self, post: Dict[str, Any]) -> Dict[str, Any]:
        text = post.get("text", "")

        # Actualmente solo heurísticas
        result = self._heuristic_classification(text)

        return result
