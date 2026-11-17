# Anime MCP

Servidor Node.js/TypeScript de solo lectura conectado a FastAPI. Cliente de destino
elegido: ChatGPT. No llama al modelo de la fase 7 ni necesita una clave de inferencia.
Cada herramienta recibe todos sus filtros; no hay conversaciones globales compartidas.

Desde la raíz del proyecto (Node 22.16+, comprobado con Node 24):

```powershell
npm.cmd --prefix apps/mcp ci
npm.cmd --prefix apps/mcp run build
```

Iniciar primero la API Python, en otra terminal:

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py --mode rules
```

Y el MCP:

```powershell
npm.cmd --prefix apps/mcp start
```

Endpoint: `http://127.0.0.1:3001/mcp`. `/healthz` acredita solo el proceso Node;
`get_dataset_info` comprueba datos. Escucha exclusivamente en loopback y valida
Host/Origin. Está preparado para conexión privada mediante Secure MCP Tunnel;
no implementa autenticación de aplicación ni es un despliegue público.

En otra terminal:

```powershell
npm.cmd --prefix apps/mcp test
npm.cmd --prefix apps/mcp run smoke
npm.cmd --prefix apps/mcp run smoke -- --stdio
```

La prueba HTTP requiere Node y Python iniciados. La prueba stdio inicia su propio
Node y solo requiere Python. Comparan resultados completos con la API y guardan
evidencia en `docs/evidence/phase9/`. Con la web iniciada, agregar `--web` compara
también su proxy. Ninguna prueba llama al modelo.

Herramientas: `get_dataset_info`, `search_anime`, `rank_anime`, `get_anime_detail`,
`compare_anime`, `aggregate_anime`. Ver [fase 9](../../docs/09-mcp.md).

| Variable de entorno | Predeterminado | Uso |
| --- | --- | --- |
| `ANIME_API_URL` | `http://127.0.0.1:8000` | Origen de FastAPI sin ruta ni credenciales. |
| `ANIME_MCP_PORT` | `3001` | Puerto Node HTTP. |
| `ANIME_MCP_URL` | `http://127.0.0.1:3001/mcp` | URL del cliente smoke. |
| `ANIME_WEB_URL` | `http://127.0.0.1:3000` | Origen web para smoke con `--web`. |

No se carga `.env` automáticamente. El comando stdio directo es
`node apps/mcp/dist/index.js --stdio`: stdout se reserva al protocolo, los avisos
van a stderr. Usar Node directamente en configuraciones de clientes para evitar
que el banner de npm se mezcle con JSON-RPC.
