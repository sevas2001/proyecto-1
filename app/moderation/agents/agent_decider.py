import yaml
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
import os

class AgentDecider:
    """
    Aplica la política de moderación (Versión Azure AI Hub).
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

        self.prompt = ChatPromptTemplate.from_template(
            """
            Eres el agente decisor de un sistema de moderación.
            Tu objetivo es asignar el estado final a un post basándote en la clasificación previa y la política.

            POLÍTICA DE UMBRALES:
            - Riesgo alto (confianza >= {high_t}): suele ser RECHAZADO.
            - Riesgo bajo (confianza <= {low_t}): suele ser APROBADO o REVISIÓN dependiendo de la categoría.

            POLÍTICA DE CATEGORÍAS (Acciones por nivel):
            {policy_categories}

            CLASIFICACIÓN DETECTADA:
            Labels: {labels}
            Confianza: {confidence}

            TAREA:
            Decide si el post debe ser "APROBADO", "RECHAZADO" o enviado a "REVISION_HUMANA".
            Proporciona un razonamiento detallado.

            RESPONDE ÚNICAMENTE EN FORMATO JSON:
            {{
                "proposed_status": "STATUS",
                "reason": "Explicación detallada de por qué se tomó esta decisión basándose en el contexto."
            }}
            """
        )

    def decide(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        labels = classification.get("labels", [])
        confidence = classification.get("confidence", 0.0)

        if not labels:
            return {
                "proposed_status": "APROBADO",
                "reason": "No se detectaron categorías de riesgo."
            }

        try:
            thresholds = self.policy["thresholds"]
            
            chain = self.prompt | self.llm | self.output_parser
            result = chain.invoke({
                "high_t": thresholds["high_risk_threshold"],
                "low_t": thresholds["low_confidence_threshold"],
                "policy_categories": str(self.policy["categories"]),
                "labels": labels,
                "confidence": confidence
            })
            return result
            
        except Exception as e:
            worst_status = "REVISION_HUMANA"
            return {
                "proposed_status": worst_status,
                "reason": f"Decisión basada en fallback por error en IA: {str(e)}"
            }
