# Fase 7 — Integración del modelo de IA

Estado: implementación OpenAI completada y probada con proveedor simulado;
pendientes clave local, prueba real y revisión del usuario. No se afirma que
haya una llamada real completada con OpenAI en esta sesión.
La fase 6 inicial fue aprobada para la entrega del prototipo; mejoras visuales y
beta móvil quedan como trabajo posterior, no como bloqueo de esta fase.

## Objetivo

Interpretar preguntas en español con flexibilidad y ejecutar las herramientas
verificadas de fase 4 dentro del contexto e historial de fase 5. La web conserva
sus contratos de resultados y representación: el modelo no genera tablas de
datos ni cifras que sustituyan las devueltas por las herramientas.

## Flujo propuesto

1. Recibir mensaje y contexto activo validado, incluida la selección explícita.
2. Entregar al modelo esquemas de herramientas y definiciones del catálogo.
3. Recibir una intención/llamada tipada o una solicitud de aclaración.
4. Validar argumentos, filtros heredados, IDs, límites y carga de datos en Python.
5. Resolver títulos ambiguos mediante búsqueda de candidatos, sin inventar IDs.
6. Ejecutar herramientas locales; una consulta puede necesitar búsqueda antes de comparar.
7. Devolver resultados acotados al modelo para redactar la explicación.
8. Guardar resultado, evidencia, contexto e identificación del intérprete en el historial.

La web recibe la misma selección de datos para tabla y gráfico. La explicación
generada se diferencia de la evidencia calculada. Una validación adicional debe
evitar publicar cifras/IDs no sustentados en los resultados de herramientas.

## Bloques de implementación y revisión

| Bloque | Cambio | Verificación |
| --- | --- | --- |
| 7.1 Conexión | Elegir acceso y crear adaptador configurable | Una llamada real; configuración sin secretos en repositorio. |
| 7.2 Herramientas | Exponer contratos de consulta y aclaración al modelo | Rechazo de argumentos inválidos y métricas no disponibles. |
| 7.3 Contexto | Integrar interpretación en LangGraph | Refinamientos mantienen filtros; solicitudes nuevas se distinguen de cambios. |
| 7.4 Explicaciones | Redactar desde resultados reales | Cifras y registros corresponden a consulta; sin resultados ficticios. |
| 7.5 Límites y pruebas | Tiempo, llamadas, tokens, fallos y consumo | Conversación real por web y HTTP; errores conservan resultado previo. |

## Archivos que se prevé modificar

- Nuevo adaptador de proveedor y configuración del modelo en `apps/api`.
- `conversation.py`: separar interpretación por reglas y por modelo, reutilizando
  consulta, selección, composición y persistencia existentes.
- `models.py`: distinguir explícitamente `bounded_rules` de la interpretación con
  modelo y preservar compatibilidad con conversaciones ya guardadas.
- `main.py`: estado real de conexión/configuración, no una etiqueta fija de IA.
- `history.py`: registrar metadatos necesarios de ejecución sin incluir claves.
- `.env.example`, dependencias, pruebas y README.
- Web: actualizar el indicador del intérprete según respuesta de API; no simular
  que el modo de reglas usa un modelo.

## Acceso al proveedor por decidir

Opción A: API con credenciales del proyecto y control de consumo. Permite conectar
el backend directamente; requiere comprobar acceso al modelo y facturación/límites.

Opción B: Sign in with ChatGPT. La documentación consultada describe acceso al plan
para solicitudes elegibles, además de autenticación; no debe tratarse como un
simple botón que automáticamente habilita cualquier modelo o aplicación. Hay que
verificar requisitos del flujo, elegibilidad y registro/client ID antes de elegirlo.
No se usarán tokens internos ni credenciales de sesión extraídas del navegador.

La elección debe preceder a la implementación dependiente del proveedor. No se
solicitará pegar claves en el chat; las credenciales se configuran localmente.
No se fijó un modelo ni se aprobó un gasto de API por esta especificación.

## Datos enviados y límites

- Mensaje actual, contexto resumido, filtros, IDs seleccionados y esquema necesario.
- Resultados limitados de las herramientas cuando se requieran para explicar o continuar.
- No enviar los 22.634 registros ni el historial completo por defecto.
- Sinopsis y títulos se tratan como datos, nunca como instrucciones de sistema.
- Límites configurables de llamadas por turno, tokens y tiempo; valores concretos
  se acuerdan junto con el modelo y presupuesto antes de las pruebas de consumo.
- Un fallo del proveedor conserva el resultado previo y no genera un turno parcial.
- El modo de reglas puede conservarse para pruebas, pero debe identificarse y
  no activarse silenciosamente como si hubiera respondido el modelo.

## Escenarios de aceptación

- «Busco series de fantasía cortas, de hasta 12 episodios, ordenadas por puntuación».
- «De esas, solo las que se estrenaron desde 2020».
- «Ahora quitá el límite de episodios» conserva el resto de los filtros.
- «Compará estos dos» usa la selección real; sin selección pide aclaración.
- Un título con varias coincidencias muestra candidatos antes de elegir una entrega.
- «Ordená por seguidores» explica que la métrica no está disponible; no la inventa.
- API sin credenciales, timeout y parámetros inválidos generan resultados controlados.
- Varias formulaciones de una misma petición producen filtros y datos equivalentes.

Las cifras exactas se contrastarán con el servicio existente, independientemente
de cómo se redacte la respuesta. La fase no se aprueba solo con pruebas simuladas:
requiere llamada real al modelo, consulta real al dataset y resultado visible.

## Referencias consultadas

- https://developers.openai.com/api/docs/guides/function-calling
- https://developers.openai.com/siwc

## Implementación de la fase 7

El usuario solicitó realizar la integración y preguntó dónde crear la clave.
Se eligió la ruta de API de OpenAI; Sign in with ChatGPT no se implementó.
Modelo inicial configurable: `gpt-5-mini`, documentado como compatible con llamadas
a funciones. La disponibilidad concreta se valida con la cuenta del usuario.

### Adaptador y herramientas

`openai_agent.py` usa Responses API mediante httpx, ya presente en el entorno y
ahora declarado como dependencia de producción. No necesita instalar un SDK adicional.
Se envían esquemas estrictos y se validan los argumentos de nuevo en Python:

| Herramienta | Función |
| --- | --- |
| `search_titles` | Buscar candidatos y resolver IDs; no reemplaza resultados activos. |
| `query_catalog` | Consulta nueva o refinamiento de campos explícitamente enumerados. |
| `query_selected` | Detalle/comparación de la selección real, conservando filtros. |
| `inspect_current` | Consultar filtros y evidencia del resultado anterior. |
| `present_result` | Terminar el turno usando filas y destacados verificados. |
| `ask_clarification` | Pedir precisión con motivos y candidatos conocidos. |

El refinamiento aplica solo `changed_fields`; un objeto de consulta con valores
por defecto no borra los filtros heredados. IDs que no provienen de selección,
búsqueda resuelta o referencia numérica del usuario no se aceptan. Las métricas
deshabilitadas siguen fuera del contrato.

### Presentación fundamentada

El modelo elige herramientas, referencias destacadas y nivel de detalle. La prosa
factual se construye con plantillas locales y valores del resultado: puntuaciones,
conteos, episodios y diferencias absolutas en una comparación. No se publica prosa
libre del proveedor como evidencia. Esta es una restricción deliberada del prototipo:
la redacción es menos libre, pero no admite cifras o títulos inventados por el modelo.

Se envía el mensaje, filtros, selección, vocabulario del catálogo y un resumen del
resultado activo de hasta 20 filas/40 grupos. No se envían catálogo completo,
`source_values`, historial completo ni claves dentro del cuerpo. En esta versión
no se envían sinopsis al modelo: la ficha las muestra directamente del dataset.
Las respuestas están configuradas con `store=false`; esto no equivale a una
declaración de retención cero por parte del proveedor.

### Modos y estado verificable

- `ANIME_AGENT_MODE=rules`: mantiene las reglas y no llama a OpenAI.
- `ANIME_AGENT_MODE=openai`: usa herramientas del modelo; si falla, devuelve error
  controlado y no pasa silenciosamente a reglas.
- `/api/health` diferencia clave ausente, configuración sin verificar y una llamada
  real completada. Configurar una clave por sí solo no marca conexión verificada.
- `AgentResponse.interpreter` distingue `bounded_rules` y `openai_tools`.
- `model_run` guarda modelo, solicitudes, tokens reportados, herramientas,
  duración y IDs de respuesta; no guarda clave ni cuerpos de error del proveedor.
- El historial antiguo se sigue leyendo; `model_run` es opcional.
- La web muestra el modo informado por la API y el consumo reportado de cada turno.

### Persistencia y fallos

La petición remota se ejecuta fuera de la transacción de escritura de SQLite y
fuera del bucle HTTP principal. Las consultas de otras conversaciones no deben
quedar bloqueadas por una llamada al modelo. Antes de insertar se vuelve a
comprobar el turno activo. Un cambio concurrente provoca 409 sin escribir sobre
un contexto viejo. Los reintentos guardados conservan idempotencia.

Si un turno falla antes de guardarse, reintentarlo puede generar una nueva llamada
y consumo: la idempotencia local no garantiza facturación única del proveedor.
Los errores 401, 403, 404, 429, timeout y respuestas incompletas muestran mensajes
controlados sin reflejar el cuerpo bruto del proveedor ni la clave.

`selected_ids=null` u omitido permite heredar selección; `selected_ids=[]` la
limpia expresamente. Esto evita reutilizar dos filas después de que el usuario
limpió la selección en la interfaz.

### Límites del prototipo

| Variable | Predeterminado | Rango admitido |
| --- | ---: | --- |
| `ANIME_MODEL_MAX_REQUESTS` | 4 | 1–8 |
| `ANIME_MODEL_MAX_TOOL_CALLS` | 6 | 1–12 |
| `ANIME_MODEL_MAX_OUTPUT_TOKENS` | 2.048 por solicitud | 512–4.096 |
| `ANIME_MODEL_TURN_TIMEOUT` | 60 segundos por turno | 10–75 |
| `ANIME_MODEL_MAX_INPUT_CHARS` | 60.000 caracteres del cuerpo | 10.000–120.000 |

Son valores iniciales ajustables, no un presupuesto monetario aprobado ni un
límite de gasto de la cuenta. Se envía una herramienta por solicitud, sin llamadas
paralelas ni reintentos automáticos de proveedor. Una comparación por dos títulos
puede necesitar buscar cada título, consultar y presentar: cuatro solicitudes.
La web espera hasta 90 segundos para reconciliar el resultado completo.

## Crear y configurar la clave

1. Abrir https://platform.openai.com/api-keys, iniciar sesión y elegir el proyecto.
2. Crear una clave secreta. La clave completa se muestra al crearla; no pegarla
   en el chat ni incorporarla al repositorio.
3. Revisar saldo/créditos y límites en OpenAI Platform. La facturación de API es
   independiente de la suscripción ChatGPT; una clave no garantiza saldo o acceso al modelo.
4. Detener el Uvicorn anterior con Ctrl+C y ejecutar, desde `anime-data-agent`:

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py
```

El programa solicita la clave con entrada oculta, la pasa al proceso hijo mediante
su entorno y no la escribe en disco ni en los argumentos del comando. La clave
se vuelve a pedir al reiniciar salvo que ya exista en el entorno local. Si no hay
terminal interactiva, no permite una entrada oculta degradada a texto visible.
No se carga automáticamente un `.env` de la raíz.

Se puede elegir otro modelo con `--model NOMBRE`. Para usar el prototipo anterior:

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py --mode rules
```

## Pruebas y estado de validación

Resultado de la suite de backend: 24 casos, 23 aprobados y uno ASGI omitido por la
limitación ya registrada de esta sesión. Incluye 13 casos específicos de la fase 7
con proveedor simulado: esquemas, consulta real local, contexto, limpieza de
selección, candidatos ambiguos, referencia inventada, límites, redacción anclada,
errores sin secretos, rollback y concurrencia durante espera remota.

La compilación web pasó con los indicadores del modo y uso. No se ejecutó ninguna
solicitud real pagada a OpenAI; las pruebas simuladas no acreditan esa conexión.

Con la API en modo OpenAI y la clave ingresada, ejecutar en otra terminal:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_model.py --allow-api
```

Esta prueba crea una conversación real y envía tres turnos: petición libre de cinco
series de fantasía de hasta doce episodios, refinamiento desde 2020 y comparación
de dos filas seleccionadas. Comprueba filtros, intérprete y solicitudes reportadas.
Puede consumir API; sin `--allow-api` no ejecuta la prueba. El resumen de tokens
es el reportado por el proveedor, no una estimación de importe facturado.

Para revisión manual: recargar `/analisis`, comprobar que identifica OpenAI y enviar
una petición que no coincida literalmente con las antiguas frases de reglas.
No se da por cerrada la fase hasta registrar una prueba real y revisión del usuario.

## Descripción de cierre provisional

Se implementaron adaptador Responses API, herramientas estrictas, contexto con
refinamiento explícito, presentación de hechos verificados, metadatos de consumo,
arranque con clave oculta y prueba de aceptación real. Se preservó el modo de
reglas y compatibilidad de historial. Las pruebas locales y compilación pasaron.
La clave fue ingresada por el usuario. Sigue pendiente una generación real satisfactoria
por créditos agotados, y la revisión de esa capacidad. La aplicación continúa
con advertencia mediante reglas locales.

Referencias adicionales:

### Diagnóstico de la primera prueba real

El usuario informó un rechazo de autenticación inicial y, tras volver a ingresar
la clave, un rechazo de límite o cuota. El log local confirma salud 200, creación
de conversación 201 y fallo 503 al generar el turno. Esto no acredita una generación
exitosa: el 503 local representa el fallo del proveedor y conserva el resultado previo.

Se mejoró el adaptador para distinguir los códigos conocidos de créditos agotados,
cuota insuficiente, límites de gasto de proyecto/organización y límite temporal
de solicitudes/tokens. Solo se clasifican códigos conocidos; no se expone el
cuerpo bruto del proveedor. Hay una prueba adicional con proveedor simulado para
esa distinción y para verificar que no se reflejan mensajes secretos del proveedor.
La facturación o los límites de la cuenta no se modificaron. Falta una respuesta
real exitosa para cerrar la fase. Referencia:
https://help.openai.com/en/articles/5955604-troubleshooting-api-rate-limits-and-429-errors

- https://help.openai.com/en/articles/4936850-how-to-set-up-your-chatgpt-account
- https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform
- https://developers.openai.com/api/docs/models/gpt-5-mini


### Continuidad cuando la IA no está disponible

La conexión con IA es opcional para utilizar el prototipo. Al iniciar con
`scripts/start_api.py`, Enter sin clave permite continuar con reglas locales.
Si OpenAI rechaza una consulta por saldo, permisos, conexión u otra indisponibilidad
controlada, ese mismo mensaje se procesa con las reglas existentes, conservando
el contexto. El turno incluye una advertencia y declara `bounded_rules`.
Si la pregunta supera esas reglas, se solicita reformularla.

Después del primer fallo no se reintenta OpenAI durante ese proceso. Para volver
a probarlo tras resolver la causa, reiniciá la API. `/api/health` informa el modo
efectivo y `model_warning`; la interfaz muestra la advertencia. Esto no certifica
una prueba real satisfactoria del modelo: sigue pendiente por
`credit_balance_exhausted`. La validación local y la fase 8 pueden continuar.
