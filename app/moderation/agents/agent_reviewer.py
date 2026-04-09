from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
import os

class AgentReviewer:
    """
    Agente de revisión final.
    Actúa como supervisor para asegurar que decisiones críticas pasen por humanos.
    """

    def __init__(self):
        load_dotenv()
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.output_parser = JsonOutputParser()

        self.prompt = ChatPromptTemplate.from_template(
            """
            Eres el supervisor final de un sistema de moderación automatizada.
            Tu misión es determinar si la decisión tomada por los agentes previos es segura o si presenta "puntos ciegos" que requieren un humano.

            CLASIFICACIÓN: {classification}
            DECISIÓN PROPUESTA: {decision}

            CRITERIOS PARA REVISIÓN HUMANA OBLIGATORIA:
            1. Incertidumbre en el contexto (la IA no está segura).
            2. Presencia de datos personales sensibles.
            3. Ambigüedad en el tono (sarcasmo, ironía) que pueda cambiar el sentido.

            RESPONDE ÚNICAMENTE EN FORMATO JSON:
            {{
                "final_status": "STATUS_FINAL",
                "risk_notes": ["razón 1", "razón 2"]
            }}
            """
        )

    def review(self, classification: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        try:
            chain = self.prompt | self.llm | self.output_parser
            result = chain.invoke({
                "classification": classification,
                "decision": decision
            })
            
            # Forzar revisión si hay baja confianza o datos personales detectados
            if classification.get("confidence", 1.0) < 0.3 or "datos_personales" in classification.get("labels", []):
                result["final_status"] = "REVISION_HUMANA"
                result["risk_notes"].append("Activado por regla de seguridad de confianza/datos.")
            
            return result
            
        except Exception as e:
            return {
                "final_status": decision.get("proposed_status", "REVISION_HUMANA"),
                "risk_notes": [f"Error en revisión IA, usando propuesta original. Error: {str(e)}"]
            }
