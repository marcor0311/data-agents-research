# Ejecutar Anime Data Agent paso a paso (Windows)

## Elegir cómo usarlo

| Modo | Procesos necesarios | Clave necesaria |
| --- | --- | --- |
| Web local sin IA y sin MCP | API Python + web Next.js | Ninguna |
| Web local con OpenAI | API Python en modo openai + web | Clave de inferencia OpenAI y saldo disponible |
| Consultar desde ChatGPT mediante MCP | API Python + MCP Node + tunnel-client | Clave runtime con Tunnels Read + Use |
| Web y ChatGPT a la vez | API Python + web + MCP + tunnel-client | Solo la del túnel si la API usa rules |

El MCP consulta directamente las herramientas de datos: no necesita la clave de
inferencia de la fase 7. La web no necesita MCP ni túnel. El modo rules permite
consultas acotadas e historial, pero no entiende todas las preguntas de lenguaje
natural. Los datos son una captura, no tendencias en vivo.

## 1. Preparar el proyecto una sola vez

Instalar Git, Python (recomendado 3.12) y Node.js (recomendado 24; MCP exige
22.16 o superior). Abrir PowerShell o una terminal de Windows.

En esta guía, **raíz del repositorio** significa la carpeta clonada
`anime-data-agent`, donde están `README.md`, `apps/` y `scripts/`.
Abrir una terminal en esa carpeta desde el explorador de archivos o el editor.
Si la terminal está en la carpeta que la contiene, entrar con:

```powershell
cd .\anime-data-agent
```

Todos los comandos siguientes se ejecutan desde la **raíz del repositorio**.
En cada terminal nueva, abrir esa misma carpeta. Las rutas relativas no dependen
del usuario ni del lugar del clon.

Instalar las dependencias:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .\apps\api
npm.cmd --prefix apps/web ci
```

No hace falta activar el entorno virtual: los comandos usan directamente su Python.

### Preparar los datos en un clon nuevo

`data/` no se incluye en Git. Desde `anime-data-agent`, obtener el repositorio
de datos como carpeta vecina y fijar la revisión usada por el prototipo:

```powershell
git clone https://github.com/LeoRigasaki/Anime-dataset.git ..\Anime-dataset
git -C ..\Anime-dataset checkout 5d911e8eb286c0e8f17c263fb9ea7c09ceb1712c
.\.venv\Scripts\python.exe scripts/prepare_dataset.py
```

El checkout anterior es para un clon nuevo dedicado a los datos. Si esa carpeta
ya existe, comprobar su revisión y cambios antes de modificarla; no repetir el
clone. La preparación genera `data/processed/current.json`. No ejecutar los
recolectores ni subir el CSV a GitHub: su redistribución pública no está aclarada.
Ver [procedencia y calidad](03-dataset.md).

## 2. Usar la web SIN MCP y SIN clave de IA

Esta es la opción inicial más sencilla. Abrir dos terminales independientes.

### Terminal 1: API de datos

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py --mode rules
```

Esperar `Uvicorn running on http://127.0.0.1:8000`. Dejarla abierta.
No pide clave. Comprobar [salud de la API](http://127.0.0.1:8000/api/health).

### Terminal 2: página web

```powershell
npm.cmd --prefix apps/web run dev
```

Esperar `Ready` y dejarla abierta. Abrir en el navegador de esa computadora:

- [Portada](http://127.0.0.1:3000/): explorar, buscar y abrir fichas.
- [Análisis](http://127.0.0.1:3000/analisis): chat, tablas y resultados.

**Iniciar Python no inicia la página web.** Se necesitan ambas terminales.
`127.0.0.1` siempre corresponde al equipo donde se abre el navegador.

## 3. Usar la web CON modelo OpenAI (opcional)

Mantener la terminal de la web. Detener solo la API con Ctrl+C y arrancarla así:

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py --mode openai
```

Crear una clave de inferencia en [OpenAI Platform](https://platform.openai.com/api-keys).
Debe permitir solicitar respuestas mediante Responses API. Pegar la clave completa
una sola vez en la entrada oculta y presionar Enter; no se ven caracteres.
El helper no la guarda en disco. El modelo predeterminado es `gpt-5-mini`;
`--model ID_DEL_MODELO` permite elegir otro disponible en la cuenta.

La suscripción de ChatGPT y la facturación de API se administran por separado.
Los mensajes pueden generar consumo. Enter sin clave o un fallo del proveedor
permite continuar con reglas y una advertencia visible. Reiniciar la API para
volver a intentar IA. No confundir respaldo local con una prueba exitosa del modelo.

Prueba opcional con consumo autorizado por quien ejecuta el comando:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_model.py --allow-api
```

## 4. Usar el catálogo desde ChatGPT mediante MCP (opcional)

Mantener la API de la terminal 1 en modo rules. La web es opcional para este modo.
Si también se desea verla, mantener su terminal y abrir dos adicionales.

### Instalar y compilar MCP una vez

Desde `anime-data-agent`:

```powershell
npm.cmd --prefix apps/mcp ci
npm.cmd --prefix apps/mcp run build
```

### Terminal MCP

```powershell
npm.cmd --prefix apps/mcp start
```

Dejarla abierta. El endpoint privado es `http://127.0.0.1:3001/mcp`.

### Crear el túnel y su clave una vez

1. Abrir [Platform Tunnels](https://platform.openai.com/settings/organization/tunnels).
2. Crear un túnel, por ejemplo `MCP Anime`, asociado al espacio de ChatGPT previsto.
3. Para este prototipo sin una política de redes específica, dejar desactivado
   `Restrict client network access` y `Allowed CIDRs` vacío.
4. Conservar su ID `tunnel_…`: es un identificador, no la clave secreta.
5. Descargar y extraer el cliente desde las
   [publicaciones oficiales](https://github.com/openai/tunnel-client/releases/latest).
   Para Windows Intel/AMD de 64 bits, elegir el ZIP completo
   `tunnel-client-<version>-windows-amd64.zip`. Para Windows ARM, elegir arm64.
6. Crear una clave runtime en la misma organización, con permisos Restricted:
   **Tunnels Read + Use**. Guardar la clave completa; el panel no permite verla
   completa de nuevo. Esta clave no necesita permisos de inferencia.

### Terminal del túnel

Reemplazar `TU_ID_REAL` por el identificador propio. El ejemplo usa la carpeta
Descargas del usuario actual mediante `$env:USERPROFILE`; ajustar el nombre de
la carpeta si se descargó otra versión o se extrajo en otra ubicación:

```powershell
.\.venv\Scripts\python.exe scripts/start_tunnel.py --tunnel-id TU_ID_REAL --client "$env:USERPROFILE\Downloads\tunnel-client-v0.0.21-windows-amd64\tunnel-client.exe"
```

Cuando diga `Clave runtime con Tunnels Read + Use`, pegar la clave secreta del
túnel una sola vez y presionar Enter. No pegar el ID del túnel en ese campo.
Si Ctrl+V no funciona, probar clic derecho o Shift+Insert. Dejar el proceso abierto.

Abrir [panel del túnel](http://127.0.0.1:8080/ui) y comprobar disponibilidad en
[readyz](http://127.0.0.1:8080/readyz). El mensaje de proceso iniciado por sí solo
no demuestra que esté listo. Los mensajes `mcp session initialized` y
`tunnel metadata fetched` acreditan inicialización local y acceso a metadatos;
todavía hace falta consultar desde ChatGPT.

### Agregarlo en ChatGPT Desktop

1. Abrir la barra lateral de ChatGPT y entrar a **Plugins**.
2. Pulsar **+**, luego **Add custom MCP server**.
3. Nombre: `Anime Data Agent`.
4. Descripción: `Consulta, búsqueda, rankings y comparación del catálogo de anime.`
5. En **Connection**, elegir **Tunnel** y seleccionar `MCP Anime` o introducir su ID.
6. Si pide autenticación de la aplicación, elegir **None**: este prototipo no
   implementa cuentas propias; el acceso depende del túnel y sus asociaciones.
7. Revisar el aviso y crear el plugin con **Create as a plugin**.
8. Revisar las seis herramientas descubiertas e instalar el plugin si lo solicita.
9. Abrir una conversación nueva, escribir `@` y seleccionar **Anime Data Agent**.
10. Pedir: `Consultá la fuente, la fecha y la cantidad de registros del catálogo`.

Si no aparece Plugins, revisar [Plugins en la web](https://chatgpt.com/plugins)
con la misma cuenta/espacio. Los menús y la disponibilidad dependen de la versión
y las políticas de la cuenta. No poner la clave runtime en el formulario de ChatGPT.

La consulta de metadatos desde ChatGPT se comprobó en esta entrega y devolvió
22.634 registros. También se ejecutaron búsquedas de títulos. Eso no equivale a
haber completado todos los casos de aceptación de fase 9.

## 5. Detener y volver a iniciar

- Detener cada servidor con Ctrl+C en su terminal.
- Para volver a usar la web sin IA: repetir solo las dos terminales del paso 2.
- Para volver a usar ChatGPT con MCP: iniciar API, MCP y túnel. No hace falta
  recrear el plugin ni el túnel cada vez. La clave se pide otra vez si no está
  configurada en el entorno.
- Repetir instalación/compilación cuando cambien dependencias o código del MCP.
- No ejecutar dos instancias del mismo servicio en el mismo puerto.

## 6. Problemas frecuentes

| Síntoma | Qué revisar |
| --- | --- |
| No abre el puerto 3000 | Iniciar Next.js en su propia terminal y esperar Ready. |
| 404 al abrir `http://127.0.0.1:8000/` | Es la API, no la web. Abrir 3000; para API usar `/docs` o `/api/health`. |
| La web abre pero no carga datos | Revisar API en 8000 y preparación del dataset. |
| Falta `current.json` | Preparar datos siguiendo el paso 1. |
| Puerto ocupado / EADDRINUSE | Buscar la terminal propia ya abierta y reutilizarla o detenerla con Ctrl+C. |
| `401 invalid_api_key` en túnel | Detener solo el túnel y volver a pegar la clave completa; una clave abreviada o duplicada no sirve. |
| Error de permisos en túnel | Revisar Tunnels Read + Use y organización/asociación del túnel. |
| `credit_balance_exhausted` en modo openai | Revisar saldo de inferencia; se puede seguir con rules. |
| No aparece el túnel en ChatGPT | Revisar cuenta, espacio y asociaciones en Platform. |
| Muchas líneas INFO en túnel | Son registros de inicio; revisar WARN/ERROR y estado real de disponibilidad. |
| Se cierra el servidor ejecutado por un asistente | Arrancarlo en una terminal propia; el entorno del asistente puede bloquear procesos o conexiones. |

## 7. Verificación y publicación en GitHub

Sin llamar al modelo:

```powershell
.\.venv\Scripts\python.exe scripts/validate_project.py
```

Con API y MCP iniciados, comprobar la integración local:

```powershell
npm.cmd --prefix apps/mcp run smoke
```

Antes de hacer commit, revisar `git status` y el diff. Publicar código y
documentación; no incluir claves, `.env` con secretos, `.venv`, `node_modules`,
`.next`, historial local ni datos descargados. No pegar claves en comandos que
queden en el historial. El helper de túnel las recibe mediante entrada oculta.

Ver también [README](../README.md), [modelo IA](07-modelo-ia.md) y [MCP](09-mcp.md).
