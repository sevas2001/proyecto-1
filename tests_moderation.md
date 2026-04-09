# Bancos de Prueba para ModerApp 🛡️

Copia y pega estos ejemplos en la pestaña **"✏️ Crear post"** de la aplicación para verificar cómo reaccionan los agentes inteligentes de Azure.

---

## 🟢 CASOS: APROBACIÓN ESPERADA
Mensajes positivos o neutrales que no violan ninguna política.

1. **Viaje:** "¡Increíble fin de semana en la montaña! El paisaje era espectacular y el aire súper puro. #naturaleza #relax"
2. **Gastronomía:** "He probado la mejor hamburguesa de la ciudad hoy. Totalmente recomendada. ¿Alguien sabe de algún buen sitio de postres cerca?"

---

## 🔴 CASOS: RECHAZO ESPERADA (Detección de Riesgo)
Mensajes que violan claramente las políticas de spam, odio o violencia.

3. **Spam/Estafa (Inversión):** "¡Gana 5000€ al día sin salir de casa! Inversión garantizada con Bitcoin. Solo hoy, haz click aquí: http://cripto-estafa.com/rico-ya"
4. **Odio/Acoso:** "Eres un absoluto desperdicio de espacio, no entiendo cómo alguien puede seguirte. Deberías borrar tu cuenta, maldita escoria."
5. **Violencia:** "Te voy a buscar a tu casa y vas a pagar por lo que hiciste. Sé dónde vives y no vas a poder escapar."

---

## 🟡 CASOS: REVISIÓN HUMANA (Detección Sensible / Dudosa)
Mensajes que contienen datos personales o son ambiguos, por lo que el `AgentReviewer` debería derivarlos a un humano.

6. **Datos Personales:** "Hola Pedro, te paso mi teléfono para que me llames y coordinemos lo de la cena: 677889900. ¡Hablamos!"
7. **Sarcasmo / Ambigüedad:** "Uff, sí, me encanta que me ignoren durante tres días. Es mi actividad favorita del mundo. Sigue así, campeón."
8. **Contacto Directo:** "Si quieres los archivos, escríbeme a mi correo privado: contacto_secreto@gmail.com"

---

## 🧠 ¿QUÉ OBSERVAR EN EL "TRACE"?
Al publicar, abre la pestaña **"📋 Auditoría"** para ver el razonamiento de la IA:
- **Labels:** ¿Ha identificado la categoría correcta (spam, odio, datos_personales)?
- **Confidence:** ¿Qué tan segura está la IA?
- **Reason:** Lee la explicación que da el `AgentDecider`. Debería ser mucho más natural que antes.
