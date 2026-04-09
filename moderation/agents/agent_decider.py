import yaml
from typing import Dict, Any
from langchain.prompts import ChatPromptTemplate


class AgentDecider:
    """
    Aplica la política de moderación.
    Preparado para razonamiento LLM en el futuro.
    """

    def __init__(self, policy_path: str):
        with open(policy_path, "r", encoding="utf-8") as f:
            self.policy = yaml.safe_load(f)

        self.prompt = ChatPromptTemplate.from_template(
            """
            Dadas las categorías detectadas {labels}
            y una confianza de {confidence},
            decide el estado del contenido.
            """
        )

    def decide(self, classification: Dict[str, Any]) -> Dict[str, Any]:
        labels = classification["labels"]
        confidence = classification["confidence"]

        thresholds = self.policy["thresholds"]
        low_t = thresholds["low_confidence_threshold"]
        high_t = thresholds["high_risk_threshold"]

        if not labels:
            return {
                "proposed_status": "APROBADO",
                "reason": "No se detectaron categorías de riesgo."
            }

        worst_status = "APROBADO"
        reasons = []

        for label in labels:
            category = self.policy["categories"].get(label)
            if not category:
                continue

            if confidence >= high_t:
                level = "high"
            elif confidence <= low_t:
                level = "low"
            else:
                level = "medium"

            action = category["action"][level]
            reasons.append(f"{label} ({level})")

            if action == "RECHAZADO":
                worst_status = "RECHAZADO"
            elif action == "REVISION_HUMANA" and worst_status != "RECHAZADO":
                worst_status = "REVISION_HUMANA"

        return {
            "proposed_status": worst_status,
            "reason": f"Categorías detectadas: {', '.join(reasons)}."
        }
