# Fase 8: validación y documentación

Entrega lista para revisión del usuario. Ejecutada el 16 de noviembre de 2026
(Costa Rica; los nombres de carpetas de evidencia utilizan UTC).

## Resultado y evidencia

Informe: [summary.json](evidence/phase8/20261117T031650094841Z/summary.json).
Cada comprobación tiene su salida completa en esa misma carpeta.

| Comprobación | Resultado |
| --- | --- |
| Dependencias Python (`pip check`) | Correctas. |
| Normalización y protección de cargas | 5 pruebas aprobadas. |
| Consultas, conversación, historial, modelo simulado y continuidad | 27 pruebas aprobadas; 1 ASGI omitida. |
| Ejemplos de aceptación con captura fijada | 6 aprobados. |
| Conversación completa directa, LangGraph y SQLite temporal | Correcta; transcripción guardada. |
| Imágenes con proveedor simulado | 4 pruebas aprobadas. |
| TypeScript | Sin errores. |
| Compilación Next.js | Correcta para portada, análisis y ruta de imágenes. |
| Nuevo intento HTTP en esta sesión | Bloqueado por permisos de sockets: WinError 10013. |
| Modelo OpenAI real | Pendiente; usuario informó `credit_balance_exhausted`. |

La suite valida, entre otros, orden contra CSV original, votos opcionales,
agregación sobre todos los filtrados, entrada inválida, dataset corrupto,
ambigüedad, aislamiento, persistencia, idempotencia, conflictos y recuperación.
Comprueba que el fallo controlado del modelo permite reglas con advertencia,
sin reintentar el proveedor en cada turno. Los errores ajenos al modelo se conservan.

Los [casos de aceptación](acceptance-cases.json) registran consultas y resultados
esperados para la fuente SHA256
`9f73ed290e1be7a45ec9b0772077aaedcf490660d4196e0cf1d56465072d980c`.
El comprobador exige ese hash antes de comparar resultados. Una captura distinta
requiere una revisión consciente de expectativas. La carga completa contiene
22.634 registros; su manifiesto y archivos se verifican al abrir el repositorio.

## Repetición

Desde la raíz, después de instalar dependencias y preparar datos según README:

```powershell
.\.venv\Scripts\python.exe scripts/validate_project.py
```

No requiere una clave ni envía consultas a OpenAI. Crea una carpeta nueva con logs,
duraciones, códigos de salida y resumen. No sobrescribe ejecuciones anteriores.
`evidence/phase8/latest.json` señala la última. Una comprobación fallida produce
salida distinta de cero; los logs permiten identificar la causa.

Para añadir HTTP, arrancar previamente `scripts/start_api.py --mode rules`
en otra terminal y ejecutar el validador con `--http`. El chequeo HTTP comprueba
el modo antes de enviar mensajes y crea una conversación de demostración.
La ejecución anterior informada por el usuario en fases 4 y 5 fue satisfactoria;
no sustituye una nueva verificación de esta versión.

Entorno comprobado: Windows, Python 3.12, Node 24, dependencias del proyecto ya
instaladas. No se ha comprobado una instalación desde cero en otra computadora.
Las pruebas TypeScript de imágenes requieren Node moderno con eliminación de tipos.

## Demostración y límites

Seguir [08-demo.md](08-demo.md) para ranking, refinamiento, comparación, gráficos,
historial y procedencia. La revisión visual anterior de fase 6 fue aprobada por
el usuario; en esta fase no se ejecutó automatización de navegador. El build
correcto no acredita interacciones visuales ni accesibilidad completa.

El prototipo permite trabajo local sin IA; sus reglas admiten un vocabulario
acotado. OpenAI amplía la interpretación cuando está disponible. Las imágenes
dependen de servicios externos y sus pruebas usan simulaciones. El catálogo
representa una captura, incluye entregas futuras y no certifica tendencias actuales.
Los campos de usuarios sin datos fiables siguen deshabilitados.

Pendientes de entrega posterior: validación real del modelo, nueva comprobación
HTTP desde la terminal del usuario, mejoras visuales identificadas, adaptación
móvil y MCP. No se implementó la fase 9. Esta entrega está pensada para uso local;
no incluye autenticación ni un despliegue público.

## Qué se realizó

Se unificaron los chequeos en un comando, añadieron casos de aceptación con
fuente identificada y evidencia repetible, protegió la prueba HTTP frente a
llamadas accidentales al modelo, actualizó el README y preparó la demostración.
Se separan resultados aprobados, omisiones y bloqueos. Falta revisión del usuario
para aprobar esta fase y autorizar el paso a MCP.

### Comprobación posterior durante fase 9

El usuario autorizó avanzar a MCP. En esa sesión la API local fue accesible:
`smoke_api.py` pasó por HTTP real. La validación general con `--http --mcp`
también pasó, incluido build web tras regenerar una carpeta con permisos antiguos.
El [nuevo informe](evidence/phase8/20261117T041856658230Z/summary.json) conserva
esos resultados. Los bloqueos anteriores siguen documentados como históricos.
La conexión autenticada desde ChatGPT continúa pendiente en fase 9.
