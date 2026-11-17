# Plan de trabajo — Anime Data Agent

Resumen y seguimiento. La especificación detallada está en
[01-alcance.md](01-alcance.md). Actualizado el 16 de noviembre de 2026
(hora de Costa Rica; los informes de ejecución usan UTC).

Cada fase termina con una descripción de lo realizado y revisión del usuario.
Autorizar el avance no convierte una capacidad pendiente en una prueba aprobada.

## Estado por fase

| Fase | Resultado disponible | Estado y revisión |
| --- | --- | --- |
| 1. Alcance | Catálogo completo; mínimo de votos opcional, ninguno por defecto. | Aprobada. [Especificación](01-alcance.md). |
| 2. Proyecto | Next.js/TypeScript, FastAPI/Python y base de LangGraph; conexión local. | Aprobada tras verificar conexión, desconexión y recuperación. [Detalle](02-proyecto.md). |
| 3. Dataset | Carga de 22.634 registros con manifiesto, hashes y diccionario. | Aprobada. Siete métricas deshabilitadas por calidad. [Detalle](03-dataset.md). |
| 4. Consultas | Búsqueda, filtros, ranking, detalle, comparación y agregados. | Aprobada tras pruebas directas y HTTP. [Detalle](04-consultas.md). |
| 5. Conversación | LangGraph, contexto, selección, idempotencia, historial y recuperación con SQLite. | Aprobada tras verificación directa y HTTP. [Detalle](05-conversacion.md). |
| 6. Interfaz | Portada parallax/carrusel y análisis separado con chat, fichas, tablas y gráficos; tema del navegador. | Prototipo de escritorio aprobado. Mejoras visuales y móvil pendientes. [Detalle](06-interfaz.md). |
| 7. Modelo de IA | OpenAI Responses con herramientas validadas; continuidad con reglas y advertencia si no hay conexión. | Implementada; generación real pendiente por `credit_balance_exhausted`. El usuario autorizó avanzar con respaldo local. [Detalle](07-modelo-ia.md). |
| 8. Validación | Validador reproducible, casos de aceptación, evidencias, README y guion de demostración. | Entregada; el usuario autorizó continuar con fase 9. Regresión general y HTTP correctos. [Detalle](08-validacion.md). |
| 9. MCP | Node.js/TypeScript, seis herramientas de lectura, HTTP y stdio; delegación en Python. | Implementación local verificada; conexión final con ChatGPT pendiente de túnel, cuenta y resolución del bloqueo de revisión automática. [Detalle](09-mcp.md). |

## Verificación más reciente

[Informe general](evidence/phase8/20261117T041856658230Z/summary.json):
46 pruebas aprobadas (5 de preparación, 27 de backend, 4 de imágenes y 10 MCP),
una prueba ASGI omitida y seis casos de aceptación correctos. TypeScript,
compilación web y comprobación HTTP de conversación/historial pasaron.

[Evidencia MCP](evidence/phase9/README.md): descubrimiento de seis herramientas
y nueve comprobaciones con datos reales por cada transporte, HTTP y stdio.
Los resultados completos, filtros y evidencia coincidieron con la API Python.
El cliente utilizado fue el SDK de pruebas; todavía no fue ChatGPT.

No se acredita una generación OpenAI real satisfactoria, una nueva prueba visual
automatizada ni una instalación desde cero en otra computadora. Las imágenes
externas se probaron con proveedor simulado. La comprobación adicional del proxy
web durante fase 9 falló con `fetch failed`; no se presenta como aprobada.

## Pendientes para cerrar la fase 9

1. Resolver la revisión automática sobre la posible telemetría a
   `dc.services.visualstudio.com`. Su origen no se confirmó; no se reintentó el
   inicio por una vía indirecta. La solicitud de actualizar estos documentos no
   constituye autorización para esa conexión.
2. Instalar y comprobar el cliente oficial del túnel; crear o reutilizar el túnel
   de la organización/espacio correcto con permisos de lectura y uso adecuados.
3. Verificar disponibilidad y polling del túnel y descubrir las seis herramientas
   desde la cuenta de ChatGPT elegida por el usuario.
4. Ejecutar ranking, refinamiento y comparación desde ChatGPT y contrastar los
   resultados con Python y la web, guardando evidencia sin secretos.
5. Repetir la comprobación del proxy web y presentar la fase para revisión final.

El helper `scripts/start_tunnel.py` está preparado; su conexión autenticada no
se ejecutó. No se instaló el cliente de túnel ni se modificó la cuenta. El estado
actual de los procesos persistentes no se certifica con estos documentos.

## Alcance de la entrega y mejoras posteriores

El prototipo local funciona con reglas cuando la IA no está disponible; la falta
de créditos no bloquea las consultas del catálogo ni el desarrollo independiente.
Las herramientas MCP consultan directamente Python y no usan el modelo del backend.
La prueba del modelo de fase 7 sigue pendiente de acceso válido y saldo disponible.

La versión inicial de escritorio está aceptada. Mejoras visuales, accesibilidad
completa y adaptación móvil quedan para una beta; no son resultados ya validados.
Publicación, hosting, redistribución pública del dataset y autenticación de una
aplicación pública no están aprobados ni implementados como parte de este cierre.

## Fuente y material previo

Fuente estadística inicial: CSV local `anime_seasonal_20261116.csv` del repositorio
`LeoRigasaki/Anime-dataset`, basado en MyAnimeList. Se consulta una carga fijada con
hashes, no estadísticas actuales en vivo. AniList aporta referencias visuales
opcionales, sin mezclar sus puntuaciones o conteos con los datos del catálogo.

El descargador Jikan anterior falló por conectividad y no es requisito para
operar. El proyecto de Messi se usa como referencia de arquitectura y conversación;
no aporta datos al catálogo de anime.
