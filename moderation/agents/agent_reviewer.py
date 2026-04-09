from typing import Dict, Any
from langchain.prompts import ChatPromptTemplate


class AgentReviewer:
    """
    Agente de revisión final (HITL logic).
    Puede forzar revisión humana.
    """

    def __init__(self):
        self.prompt = ChatPromptTemplate.from_template(
            """
            Evalúa si el contenido debe escalarse a revisión humana.
            """
        )

    def review(self, classification: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        labels = classification["labels"]
        confidence = classification["confidence"]
        proposed = decision["proposed_status"]

        risk_notes = []

        # Regla 1: datos personales → siempre revisión
        if "datos_personales" in labels:
            risk_notes.append("Contiene datos personales.")
            return {
                "final_status": "REVISION_HUMANA",
                "risk_notes": risk_notes
            }

        # Regla 2: baja confianza
        if confidence < 0.3 and labels:
            risk_notes.append("Clasificación con baja confianza.")
            return {
                "final_status": "REVISION_HUMANA",
                "risk_notes": risk_notes
            }

        return {
            "final_status": proposed,
            "risk_notes": risk_notes
        }
