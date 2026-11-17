# Fase 9: MCP para ChatGPT

Cliente elegido por el usuario: ChatGPT. Servidor local implementado; conexión
con la cuenta y llamada desde ChatGPT pendientes. El cliente de pruebas permite
verificar el protocolo, pero no acredita todavía la integración con esa cuenta.

## Arquitectura y contexto

Node.js/TypeScript expone las consultas de FastAPI mediante el SDK oficial MCP
v2 (`server` y cliente de pruebas 2.4.0, adaptador Node 2.1.2, dependencias fijadas
por lockfile). Sirve Streamable HTTP en `127.0.0.1:3001/mcp` y stdio opcional.
Se comprobó también un cliente del protocolo 2025-06-18.

Cada llamada incluye filtros completos y es independiente. No hay historial
global ni selección compartida dentro del MCP. ChatGPT mantiene su contexto y
reenvía los filtros que quiera conservar. Las temporadas son registros distintos;
los títulos deben resolverse con búsqueda antes de elegir IDs para comparar.

Las herramientas solo llaman `/api/query` y `/api/dataset`. No utilizan el
intérprete de fase 7 ni una clave de inferencia; la conexión del túnel requiere
sus propios permisos de Platform. La aplicación web conserva su funcionamiento.

## Herramientas y contratos

| Herramienta | Parámetros principales | Resultado |
| --- | --- | --- |
| `get_dataset_info` | Ninguno | Fechas, carga, vocabularios y métricas deshabilitadas. |
| `search_anime` | `title`, filtros, orden, límite | Coincidencias con IDs. |
| `rank_anime` | Filtros, `order_by`, `direction`, `limit` | Ranking y omisiones por métrica desconocida. |
| `get_anime_detail` | `anime_id` positivo | Ficha con sinopsis y evidencia. |
| `compare_anime` | `anime_ids`: dos IDs distintos | Dos fichas en el orden solicitado. |
| `aggregate_anime` | Filtros, `group_by`: year/genre/studio | Grupos sobre todos los registros filtrados. |

Filtros admitidos: `title`, `formats`, `genres`, `genre_mode`, `studio`,
`year_from`, `year_to`, `statuses`, `min_score`, `min_votes`, `max_episodes`.
Varios géneros requieren `genre_mode=all` o `any`; Python valida vocabularios y
coherencia. Consultar valores válidos en `get_dataset_info`. Años: 1900–2200;
límite de filas: 1–100. Sin mínimo obligatorio de valoraciones.

Orden: score, popularity, scored_by, title, start_year, episodes,
duration_seconds, rank. Score sobre 10; duración en segundos por episodio;
popularidad/rank son posiciones y menor es mejor. Los nulos no se convierten en
cero. Un registro puede contribuir a varios géneros/estudios. Members y otras
métricas sin datos fiables permanecen deshabilitadas.

La salida conserva exactamente filas, grupos, filtros, conteos, definiciones y
evidencia de Python (carga, hashes, IDs y fuente). Node no realiza cálculos
alternativos. Los esquemas de entrada rechazan campos ajenos. Las seis herramientas
declaran lectura e idempotencia. Sus errores son `isError` con mensaje controlado;
no devuelven cuerpos brutos del proveedor. Espera: 15 segundos; respuesta API:
máximo 2 MiB. El modelo no puede elegir URLs de destino. No se siguen redirecciones.

## Instalación y comprobación local

Desde la raíz del proyecto (Node 22.16+, comprobado con Node 24):

```powershell
npm.cmd --prefix apps/mcp ci
npm.cmd --prefix apps/mcp run build
```

Terminal 1, con el dataset preparado:

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py --mode rules
```

Terminal 2:

```powershell
npm.cmd --prefix apps/mcp start
```

Terminal 3:

```powershell
npm.cmd --prefix apps/mcp test
npm.cmd --prefix apps/mcp run smoke
npm.cmd --prefix apps/mcp run smoke -- --stdio
```

El cliente smoke descubre herramientas y comprueba metadatos, búsqueda, ranking,
detalle, comparación, agregado, búsqueda vacía, métrica inválida e ID inexistente.
Compara resultados completos con Python. Agregar `--web` incluye el proxy web ya
iniciado: `npm.cmd --prefix apps/mcp run smoke -- --web`. No ejecutar la web en
producción mientras se está regenerando su build.

Validación general: `scripts/validate_project.py --http --mcp` con el Python del
entorno virtual. Necesita la API iniciada en modo efectivo de reglas. No inicia
servicios. Variables opcionales y comando stdio directo: [README MCP](../apps/mcp/README.md).

## Conexión con ChatGPT mediante Secure MCP Tunnel

El cliente oficial establece una conexión saliente con OpenAI para llegar al
MCP privado. No se abre un puerto público. La configuración de la cuenta no
se inspeccionó ni modificó durante esta entrega.

1. Abrir [Platform Tunnels](https://platform.openai.com/settings/organization/tunnels).
   Crear o reutilizar un túnel y verificar organización y asociación con la
   cuenta/espacio de ChatGPT de destino. Conservar el ID completo.
2. Descargar el cliente oficial compatible desde esa página o la
   [publicación oficial vigente](https://github.com/openai/tunnel-client/releases/latest).
   No está instalado ni comprobado aquí. Revisar su `help quickstart` y versión.
3. Crear/editar túneles requiere Tunnels Read + Manage. La clave runtime que los
   ejecuta necesita Tunnels Read + Use. No usar una clave admin para el proceso
   permanente ni pegar secretos en el chat o archivos versionados.
4. Mantener Python y Node iniciados; el helper pide la clave de forma oculta y
   la pasa al proceso mediante entorno, sin guardarla en disco:

```powershell
.\.venv\Scripts\python.exe scripts/start_tunnel.py --tunnel-id TU_ID_REAL --client "$env:USERPROFILE\Downloads\tunnel-client-v0.0.21-windows-amd64\tunnel-client.exe"
```

La ruta del cliente usa la carpeta Descargas del usuario actual; ajustar la
versión o ubicación según dónde se haya extraído el ZIP. Ejecutar desde la raíz
del repositorio `anime-data-agent`, donde están `apps/` y `scripts/`.

El helper apunta a `http://127.0.0.1:3001/mcp`, deshabilita descubrimiento OAuth
para este servidor sin cuentas de aplicación y deja la administración en
`http://127.0.0.1:8080/ui`. Comprobar `/readyz` y polling activo antes de conectar
ChatGPT; iniciar el proceso no acredita esos estados. Si 8080 está ocupado,
elegir otro puerto con `--health-port`.

5. En [ChatGPT Plugins](https://chatgpt.com/plugins), añadir un MCP personalizado,
   elegir Connection: Tunnel y seleccionar el mismo túnel/ID. Nombre propuesto:
   Anime Data Agent; descripción: búsqueda, rankings y comparación del catálogo
   local de anime. Este prototipo no tiene autenticación de aplicación: el
   acceso remoto depende de las asociaciones/permisos del túnel de OpenAI.
   Revisar el espacio previsto en la pantalla antes de continuar.
6. Verificar las seis herramientas y seleccionarlas en una nueva conversación.

El servidor solo escucha en loopback y valida Host/Origin; no es un despliegue
público de producción. La disponibilidad de MCP personalizados y túneles depende
de los permisos/políticas de la cuenta. Tener Plus por sí solo no acredita la
conexión. Si falta el menú o túnel, registrar el mensaje y revisar asociaciones;
no cambiar suscripción ni comprar créditos automáticamente.

## Aceptación pendiente desde ChatGPT

| Pregunta | Evidencia esperada |
| --- | --- |
| «Consultá fuente y fecha del catálogo» | get_dataset_info, carga y fecha local. |
| «Los diez animes de fantasía para TV de máximo 26 episodios mejor puntuados» | rank_anime con filtros completos; 1.022 elegibles en la captura fijada. |
| «Ahora solo desde 2020» | Filtros anteriores más year_from=2020. |
| «Compará Death Note con Shingeki no Kyojin» | Búsqueda para resolver entregas; comparación de IDs 1535 y 16498. |
| «¿Cuántas series se estrenaron por año desde 2020?» | TV, 1.731 registros y siete grupos en la captura. |

Guardar herramienta, argumentos, resultado, carga y hash; contrastar con API/web.
Si se incluyen cifras ajenas a los resultados, la aceptación falla aunque la
consulta técnica haya pasado. Registrar también estado del túnel y errores,
sin capturar claves. Estas pruebas desde ChatGPT no se ejecutaron todavía.

## Diagnóstico

| Síntoma | Acción |
| --- | --- |
| Error de API/timeout | Revisar Python en 8000, ANIME_API_URL y carga validada. |
| Puerto 3001 ocupado | Reutilizar la instancia propia o detenerla; cambiar puerto y upstream coherentemente si hace falta. |
| Node atiende pero no hay datos | Probar get_dataset_info; /healthz solo acredita Node. |
| Túnel ausente | Revisar organización, espacio y Tunnels Read + Use. |
| Túnel no listo | Revisar ayuda/doctor del cliente oficial, /readyz y polling. |
| Herramientas desactualizadas | Reiniciar servidor, refrescar conexión y abrir conversación nueva. |
| Sin créditos del modelo web | Las herramientas MCP consultan directamente Python; no usan ese intérprete. |

## Descripción de lo realizado

Se crearon servidor, transportes, contratos, diez pruebas, cliente de aceptación,
helper para el túnel y documentación. El cliente SDK ejecutó consultas reales por
HTTP y stdio, con igualdad de resultados y evidencia respecto a Python. Ver
[evidencia](evidence/phase9/README.md). Falta instalar/configurar el cliente de
túnel y demostrar ranking/comparación desde la cuenta de ChatGPT del usuario.
Estado: servidor local verificable; fase en revisión con conexión remota pendiente.

### Bloqueo observado al finalizar

La revisión automática rechazó una comprobación del proceso persistente por una
posible conexión de telemetría a `dc.services.visualstudio.com`. Su origen no se
confirmó; la búsqueda en los archivos instalados del MCP no encontró ese destino.
Se preservaron los resultados anteriores, sin reintentar el arranque mediante
otro mecanismo. La comprobación adicional del proxy web no pasó. Antes de seguir
con servicios persistentes y ChatGPT, resolver esa revisión o contar con la
autorización explícita correspondiente. Ver detalle en la evidencia.

Referencias revisadas:

- [SDK TypeScript v2](https://ts.sdk.modelcontextprotocol.io/v2/).
- [HTTP](https://ts.sdk.modelcontextprotocol.io/v2/serving/http.html) y [stdio](https://ts.sdk.modelcontextprotocol.io/v2/serving/stdio.html).
- [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).
- [Conectar en ChatGPT](https://developers.openai.com/plugins/deploy/connect-chatgpt).
- [Onboarding oficial](https://github.com/openai/tunnel-client/blob/master/docs/onboarding.md).
