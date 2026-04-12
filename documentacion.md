# Diseño del Sistema de Moderación Multi‑Agente

**Proyecto:** Sistema de Moderación Automatizada  
**Arquitectura:** Multi‑agente con orquestación lineal mediante LangGraph  


---

# 1. Introducción

Este documento describe la arquitectura técnica del sistema de moderación automatizada basado en un enfoque multi‑agente.

El sistema está diseñado para analizar publicaciones de usuarios (texto e imagen opcional), aplicar una política de moderación configurable y emitir una decisión trazable y auditable.

La arquitectura sigue un patrón de **orquestación lineal**, coordinado por un componente central (`Orchestrator`) que gestiona el flujo entre agentes especializados.

---

# 2. Descripción de los Agentes

El sistema se compone de tres agentes principales, cada uno con responsabilidades claramente delimitadas.

---

## 2.1 Agent Classifier

**Tipo:** Agente analítico multimodal  
**Rol:** Análisis inicial del contenido  

### Responsabilidades
- Analizar el texto del post.
- Procesar imagen asociada (si existe).
- Detectar categorías de riesgo definidas en la política.
- Generar señales explicativas de la clasificación.
- Estimar un nivel de confianza global.

### Entrada
- `post.text` (string)
- `post.image_path` (opcional)

### Salida
- `labels`: categorías detectadas.
- `confidence`: nivel de confianza.
- `signals`: evidencias o patrones activados.

### Tecnologías
- Python
- Modelos LLM (OpenAI GPT‑4o)
- Procesamiento multimodal
- RegEx y heurísticas locales

Este agente actúa como **sensor inteligente del sistema**, transformando contenido no estructurado en información estructurada procesable por los siguientes agentes.

---

## 2.2 Agent Decider

**Tipo:** Agente normativo  
**Rol:** Aplicación de la política de moderación  

### Responsabilidades
- Evaluar la clasificación generada.
- Consultar la política externa (`policy.yaml`).
- Determinar el estado propuesto:
  - `APROBADO`
  - `RECHAZADO`
  - `REVISION_HUMANA`
- Generar una justificación argumentada.

### Entrada
- Resultado del `AgentClassifier`.

### Salida
- `proposed_status`
- `reason`

### Tecnologías
- Python
- LLM para razonamiento estructurado
- Archivo de configuración `policy.yaml`

Este agente separa claramente el **análisis del contenido** de la **aplicación normativa**, mejorando mantenibilidad y auditabilidad.

---

## 2.3 Agent Reviewer

**Tipo:** Agente de validación y control de riesgo  
**Rol:** Verificación final del proceso automático  

### Responsabilidades
- Revisar clasificación y decisión propuesta.
- Detectar inconsistencias o baja confianza.
- Forzar revisión humana cuando sea necesario.
- Emitir estado definitivo del sistema.

### Entrada
- Resultado de clasificación.
- Decisión propuesta.

### Salida
- `final_status`
- `risk_notes`

### Tecnologías
- Python
- LLM para verificación semántica

Este agente actúa como **mecanismo de seguridad**, reduciendo el riesgo de decisiones automáticas incorrectas.

---

# 3. Diagrama de Orquestación

## 3.1 Diagrama de Flujo

```mermaid
flowchart TD

    User[Usuario crea post] --> Orch[Orchestrator]

    Orch --> Classifier[Agent Classifier]
    Classifier --> Decider[Agent Decider]
    Decider --> Reviewer[Agent Reviewer]

    Reviewer -->|APROBADO| Publish[Publicar contenido]
    Reviewer -->|RECHAZADO| Block[Rechazar contenido]
    Reviewer -->|REVISION_HUMANA| Human[Moderador humano]

    Human --> Final[Decisión final registrada]

    subgraph Auditoría
        Logs[Logs.jsonl]
    end

    Classifier --> Logs
    Decider --> Logs
    Reviewer --> Logs
```text

---

## 3.2 Explicación del Flujo

1. El usuario crea un post.
2. El `Orchestrator` inicializa el estado compartido.
3. El `AgentClassifier` analiza el contenido.
4. El `AgentDecider` aplica la política normativa.
5. El `AgentReviewer` valida la decisión.
6. Se determina el estado final.
7. Cada agente registra su salida en `logs.jsonl` para garantizar trazabilidad.

---

## 3.3 Estado Compartido

El sistema utiliza un objeto estructurado (`ModerationState`) que viaja entre agentes e incluye:

- Post original.
- Clasificación.
- Decisión propuesta.
- Resultado final.
- Justificación.
- Trazabilidad detallada.

Este enfoque garantiza consistencia, transparencia y auditabilidad.

---

## 3.4 Papel del Orchestrator

El `Orchestrator`:

- Define el orden secuencial de ejecución.
- Gestiona el estado compartido.
- Maneja excepciones globales.
- Garantiza degradación segura a revisión humana.
- Centraliza la trazabilidad.

No toma decisiones de contenido; su función es estrictamente de coordinación.

---

## 3.5 Justificación del Uso de LangGraph

LangGraph permite modelar explícitamente la arquitectura como un grafo dirigido de agentes, proporcionando:

- Modularidad.
- Escalabilidad futura.
- Claridad estructural.
- Extensibilidad sin rediseño global.

Aunque la orquestación actual es lineal, el diseño permite incorporar bifurcaciones condicionales en el futuro.

---

# 4. Justificación de Decisiones de Diseño

## 4.1 Arquitectura Multi‑Agente

Se adopta una arquitectura multi‑agente para:

- Separar responsabilidades.
- Facilitar mantenimiento.
- Permitir evolución independiente de cada componente.
- Reducir complejidad cognitiva.

Cada agente resuelve un problema específico dentro del pipeline.

---

## 4.2 Orquestación Lineal

Se opta por flujo lineal debido a:

- Mayor previsibilidad.
- Trazabilidad clara.
- Reducción de ambigüedad.
- Adecuación a un MVP académico.

La linealidad facilita la defensa técnica y la auditoría.

---

## 4.3 Separación de Responsabilidades

La división en análisis, decisión y revisión:

- Permite testeo aislado.
- Reduce acoplamiento.
- Mejora legibilidad arquitectónica.
- Facilita reemplazo de componentes.

---

## 4.4 Política Externa (`policy.yaml`)

Separar la política del código:

- Permite actualización sin modificar lógica.
- Facilita auditoría normativa.
- Reduce riesgo de reglas embebidas.
- Mejora adaptabilidad a nuevas regulaciones.

---

## 4.5 Trazabilidad Mediante Logs

El registro en `logs.jsonl` garantiza:

- Auditoría posterior.
- Explicabilidad.
- Control de calidad.
- Transparencia institucional.

Es un elemento crítico en sistemas que toman decisiones automáticas.

---

## 4.6 Degradación a Revisión Humana

Ante baja confianza, ambigüedad o error técnico, el sistema deriva automáticamente a revisión humana.

Este patrón prioriza:

- Seguridad.
- Justicia procedimental.
- Responsabilidad ética.

---

# 5. Conclusión

El sistema implementa una arquitectura multi‑agente robusta, modular y auditable, con:

- Coordinación centralizada mediante Orchestrator.
- Especialización funcional de agentes.
- Política desacoplada.
- Registro exhaustivo de decisiones.
- Mecanismo de seguridad basado en intervención humana.

La solución es técnicamente coherente, extensible y alineada con buenas prácticas en sistemas inteligentes regulados.
