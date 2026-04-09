import os
import json
import re
from datetime import datetime
from typing import TypedDict, Dict, Any, List

from langgraph.graph import StateGraph, END

from moderation.agents.agent_classifier import AgentClassifier
from moderation.agents.agent_decider import AgentDecider
from moderation.agents.agent_reviewer import AgentReviewer

MODERATION_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.dirname(MODERATION_DIR)

POLICY_PATH = os.path.join(MODERATION_DIR, "policy.yaml")
LOG_PATH = os.path.join(APP_DIR, "storage", "logs.jsonl")


# =====================================================
# ESTADO COMPARTIDO DEL GRAFO
# =====================================================

class ModerationState(TypedDict):
    post: Dict[str, Any]
    classification: Dict[str, Any]
    decision: Dict[str, Any]
    review: Dict[str, Any]
    status: str
    reason: str
    trace: List[Dict[str, Any]]


# =====================================================
# UTILIDADES
# =====================================================

def ensure_log_path():
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)


def mask_sensitive(text: str) -> str:
    text = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_MASKED]", text)
    text = re.sub(r"\b\d{9,15}\b", "[PHONE_MASKED]", text)
    return text


def write_log(post_id: str, agent: str, summary: str, status_after: str):
    ensure_log_path()

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "post_id": post_id,
        "agent": agent,
        "output_summary": mask_sensitive(summary),
        "status_after": status_after
    }

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


# =====================================================
# NODOS DEL GRAFO
# =====================================================

def classifier_node(state: ModerationState) -> ModerationState:
    classifier = AgentClassifier(POLICY_PATH)
    result = classifier.classify(state["post"])

    state["classification"] = result

    state["trace"].append({
        "stage": "classifier",
        "timestamp": datetime.utcnow().isoformat(),
        "output": result
    })

    write_log(state["post"]["id"], "classifier", str(result), "IN_PROGRESS")

    return state


def decider_node(state: ModerationState) -> ModerationState:
    decider = AgentDecider(POLICY_PATH)
    result = decider.decide(state["classification"])

    state["decision"] = result

    state["trace"].append({
        "stage": "decider",
        "timestamp": datetime.utcnow().isoformat(),
        "output": result
    })

    write_log(
        state["post"]["id"],
        "decider",
        result["reason"],
        result["proposed_status"]
    )

    return state


def reviewer_node(state: ModerationState) -> ModerationState:
    reviewer = AgentReviewer()
    result = reviewer.review(
        state["classification"],
        state["decision"]
    )

    state["review"] = result
    state["status"] = result["final_status"]
    state["reason"] = state["decision"]["reason"]

    state["trace"].append({
        "stage": "reviewer",
        "timestamp": datetime.utcnow().isoformat(),
        "output": result
    })

    write_log(
        state["post"]["id"],
        "reviewer",
        str(result),
        result["final_status"]
    )

    return state


# =====================================================
# CONSTRUCCIÓN DEL GRAFO
# =====================================================

def build_graph():
    graph = StateGraph(ModerationState)

    graph.add_node("classifier", classifier_node)
    graph.add_node("decider", decider_node)
    graph.add_node("reviewer", reviewer_node)

    graph.set_entry_point("classifier")

    graph.add_edge("classifier", "decider")
    graph.add_edge("decider", "reviewer")
    graph.add_edge("reviewer", END)

    return graph.compile()


# =====================================================
# FUNCIÓN PÚBLICA (CONTRATO CON PERSONA A)
# =====================================================

def moderate_post(post: Dict[str, Any]) -> Dict[str, Any]:
    try:
        graph = build_graph()

        initial_state: ModerationState = {
            "post": post,
            "classification": {},
            "decision": {},
            "review": {},
            "status": "PENDIENTE",
            "reason": "",
            "trace": []
        }

        final_state = graph.invoke(initial_state)

        write_log(
            post["id"],
            "orchestrator",
            "Moderación completada",
            final_state["status"]
        )

        return {
            "status": final_state["status"],
            "reason": final_state["reason"],
            "trace": final_state["trace"]
        }

    except Exception as e:
        write_log(
            post.get("id", "unknown"),
            "orchestrator",
            f"Error: {str(e)}",
            "REVISION_HUMANA"
        )

        return {
            "status": "REVISION_HUMANA",
            "reason": "Fallo en moderación automática",
            "trace": []
        }
