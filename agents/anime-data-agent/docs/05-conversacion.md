# Fase 5 — Conversación e historial

Estado: grafo y persistencia verificados directamente y por HTTP real con datos
locales. Pendiente aprobación conjunta con la fase 4.

## Implementación y límites

`conversation.py` implementa LangGraph con tres pasos: resolver → consultar →
componer. Usa las herramientas de fase 4; no duplica cálculos ni simula datos.
El intérprete es acotado y determinista (`interpreter=bounded_rules`). Un modelo
de IA se conectará en fase 7. La interfaz de chat corresponde a fase 6.

## Frases soportadas

| Mensaje | Efecto |
| --- | --- |
| `Busca Death Note` | Nueva búsqueda por título, sin heredar filtros anteriores. |
| `Muéstrame los 10 animes de fantasía mejor puntuados` | Nuevo ranking de fantasía por puntuación. |
| `Muéstrame los 10 animes de acción y fantasía mejor puntuados` | Exige ambos géneros; con «o», cualquiera. |
| `Solo series de televisión de máximo 26 episodios` | Refina el contexto y conserva género, orden y límite. |
| `Solo TV` | Refina únicamente el formato. |
| `Máximo 26 episodios` | Refina únicamente máximo de episodios. |
| `Desde 2020` | Refina año mínimo. |
| `Mínimo de 1000 valoraciones` | Activa el filtro opcional. |
| `Sin mínimo de valoraciones` | Elimina ese filtro. |
| `Sin límite de episodios` | Elimina máximo de episodios. |
| `Todos los formatos` | Elimina filtro por formato. |
| `Ordénalos por popularidad` | Cambia orden; permite dirección ascendente/descendente. |
| `Compara estos dos` | Requiere dos IDs seleccionados del resultado activo; conserva filtros. |
| `Ese anime` | Requiere un único ID seleccionado del resultado activo. |
| `Compara Death Note con Shingeki no Kyojin` | Nueva comparación por títulos exactos inequívocos. |
| `Compara 1535 con 16498` | Nueva comparación explícita por IDs del catálogo. |
| `Detalle de 1535` | Nueva consulta de detalle por ID. |
| `¿Cuántas series se estrenaron por año desde 2020?` | Nuevo agregado de registros TV por año de estreno. |
| `¿Qué filtros aplicaste y de dónde vienen los datos?` | Explica fuente, versión, filtros y orden; conserva resultado. |

Las variantes contempladas están en el código y pruebas. Esto no promete
comprender cualquier frase. No se permiten parcialmente instrucciones adicionales
no reconocidas. Un género desconocido, una referencia sin selección o un título
ambiguo pide aclaración y conserva estado, filtros y resultado anteriores.
La búsqueda devuelve candidatos, nunca elige por sí sola una temporada.

Los filtros de estudio, puntuación o estado están disponibles por API de consultas,
pero no tienen aún una frase de interpretación para todas sus combinaciones.
Una nueva búsqueda/ranking o comparación explícita es distinta de un refinamiento;
solo este último hereda el contexto anterior.

## Contrato de conversación

| Método y ruta | Operación |
| --- | --- |
| `POST /api/conversations` | Crea conversación con ID y turno activo inicialmente nulo. |
| `GET /api/conversations/{id}` | Recupera historial completo y puntero activo. |
| `POST /api/conversations/{id}/turns` | Envía mensaje, turno base y selección opcional. |
| `POST /api/conversations/{id}/activate` | Recupera un turno validando el puntero esperado. |

Cada turno exige `message` y `base_turn_id` (null explícito en el primero).
`selected_ids` admite hasta dos IDs del resultado anterior de esta conversación.
`request_id` es opcional y permite reintentos idempotentes: repetir el mismo cuerpo
e ID devuelve el mismo turno sin insertarlo otra vez. Reutilizarlo con otro cuerpo
devuelve 409. Una repetición no cambia el puntero activo de una conversación
que ya continuó por otros turnos.

Ejemplo de primer cuerpo:

```json
{
  "message": "Muéstrame los 10 animes de fantasía mejor puntuados",
  "base_turn_id": null,
  "request_id": "demo-turno-1"
}
```

La respuesta incluye ID del turno, padre, fecha, mensaje y `response`, con:
`status`, `explanation`, `state`, `result`, `visualization_action` e `interpreter`.
`state` conserva consulta canónica, carga y selección. `result` contiene los datos
que usará la futura interfaz. `create/update/retain` expresa cómo presentar el
resultado; todavía no hay gráficos implementados en web.

Para recuperar se envía `turn_id` y `expected_active_turn_id`. El siguiente mensaje
usa el turno recuperado como base y se guarda como una rama nueva del historial.

## Persistencia, aislamiento y fallos

`history.py` guarda SQLite en `ANIME_CONVERSATION_DB`, por defecto
`data/conversations.sqlite3`. Las lecturas son consistentes y las escrituras usan
transacciones con comprobación del turno activo. No se actualizan resultados antiguos.
La recuperación tras reiniciar vuelve a leer la misma base; no requiere Jikan.

- Turno base desactualizado: 409 y sin escritura.
- Activación de turno de otra conversación: 404.
- Selección ajena al resultado: aclaración sin aplicar cambios de filtros.
- Excepción durante el grafo: rollback, sin turno parcial.
- Error de almacenamiento: 503 y mensaje controlado.
- Carga distinta de la guardada en el contexto: pide iniciar otra conversación;
  no aplica resultados de dos versiones como si fueran la misma.
- Si falta el dataset no se invocan herramientas ni se guarda un turno ficticio;
  el historial ya guardado sigue siendo recuperable por su endpoint.

No hay autenticación multiusuario ni publicación remota en estas fases. Los IDs
separan conversaciones locales, pero no sustituyen permisos de usuario; eso debe
resolverse antes de exponer el servicio a terceros.

## Evidencia y revisión

La suite ejecutada contiene 11 casos: 10 pasaron y uno ASGI/HTTP está omitido por
defecto tras quedar bloqueado en el bucle de eventos de esta sesión. No se afirma
que el HTTP de las nuevas rutas haya pasado. Puede activarse con `ANIME_HTTP_TESTS=1`
en un entorno que lo permita; la prueba TCP separada está en `scripts/smoke_api.py`.

Se verificaron: ranking contra CSV original, refinamiento, comparación con selección,
aclaración sin cambios, explicación de evidencia, recuperación y nueva rama,
reapertura de SQLite, aislamiento, turno desactualizado, idempotencia y rollback.
La demostración directa se reproduce con:

```powershell
.\.venv\Scripts\python.exe scripts/demo_local.py
```

La evidencia guardada en `docs/evidence/04-05-demo.json` identifica expresamente
ejecución directa, sin sockets y sin modelo. Sus cifras se refieren a la carga local.

## Comprobación HTTP desde el equipo del usuario

Reiniciar la API que seguía ejecutando el código anterior (Ctrl+C y el comando
de arranque del README), con el puntero correcto:

```powershell
$env:ANIME_DATASET_PATH = 'data/processed/current.json'
.\.venv\Scripts\python.exe -m uvicorn anime_agent.main:app --host 127.0.0.1 --port 8000
```

Desde otra terminal en `anime-data-agent`:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_api.py
```

El script crea una conversación de demostración real en el historial local y
comprueba ranking, comparación, reintento, errores y recuperación. No borra
conversaciones existentes. Si Next.js sigue en ejecución, la pantalla de estado
mostrará carga validada y conversación acotada al comprobar conexión.

## Descripción para cierre

Se implementó una conversación verificable sobre el dataset con estado e historial
persistentes. Las pruebas del servicio, grafo y HTTP real pasaron. Falta recibir
aprobación conjunta del usuario. No se implementó un modelo,
chat web, diseño visual final ni MCP, que pertenecen a fases posteriores.

## Resultado HTTP aportado por el usuario

El usuario ejecutó `scripts/smoke_api.py` y confirmó éxito en dataset, ranking,
validación, conversación, comparación, idempotencia e historial por HTTP real.
La ejecución usó 22.634 registros y creó la conversación local
`69ab3f5c-ead1-4d93-9a1a-2f055c65bdd1`.
Queda registrada como comprobación informada por el usuario, distinta de la
prueba ASGI bloqueada en esta sesión. La fase 6 permanece sin iniciar.
