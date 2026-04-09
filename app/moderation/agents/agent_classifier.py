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
    Agente de clasificación (Versión Azure AI Hub).
    """

    def __init__(self, policy_path: str):
        with open(policy_path, "r", encoding="utf-8") as f:
            self.policy = yaml.safe_load(f)

        load_dotenv()
        
        # Usamos ChatOpenAI con base_url para compatibilidad con el proxy de GenIA
        self.llm = ChatOpenAI(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            base_url=f"{os.getenv('AZURE_OPENAI_ENDPOINT')}/v1",
            temperature=0
        )
        
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

    def classify(self, post: Dict[str, Any]) -> Dict[str, Any]:
        text = post.get("text", "")
        heuristics = self._heuristic_classification(text)
        
        try:
            chain = self.prompt | self.llm | self.output_parser
            categories_str = ", ".join(self.policy["categories"].keys())
            
            ai_result = chain.invoke({
                "text": text,
                "policy_categories": categories_str
            })
            
            ai_result["signals"] = list(set(ai_result.get("signals", []) + heuristics["signals"]))
            return ai_result
            
        except Exception as e:
            heuristics["signals"].append(f"llm_error: {str(e)}")
            return heuristics
