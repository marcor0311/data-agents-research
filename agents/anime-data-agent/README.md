# Anime Data Agent

Aplicación local en construcción para explorar el catálogo de anime en español.
FastAPI/Python ofrece las consultas; LangGraph interpreta los mensajes acotados
y SQLite conserva el historial. Next.js/TypeScript ofrece portada y espacio de análisis.

## Inicio paso a paso

Ver la [guía completa de ejecución en Windows](docs/10-ejecucion-paso-a-paso.md):
instalación desde un clon nuevo, datos, web sin clave de IA ni MCP, OpenAI
opcional, MCP con ChatGPT Desktop, reinicio y solución de problemas.

Las rutas de esta documentación son relativas a la **raíz del repositorio**
(la carpeta clonada `anime-data-agent`), donde están `apps/` y
`scripts/`. Abrir cada terminal en esa carpeta.

Para el uso habitual **sin IA y sin MCP**, desde `anime-data-agent`, mantener
abiertas dos terminales:

**Terminal 1 — API:**

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py --mode rules
```

**Terminal 2 — web:**

```powershell
npm.cmd --prefix apps/web run dev
```

Esperar `Ready` y abrir [la portada](http://127.0.0.1:3000/) o
[el análisis](http://127.0.0.1:3000/analisis). El puerto 8000 sirve la API;
no contiene la página web. Cerrar una terminal detiene su servidor.

## Estado

- Alcance: catálogo completo con filtros por formato.
- Rankings: criterio explícito; cantidad de valoraciones visible cuando esté validada.
  No se exige un mínimo por defecto; se permitirá como filtro opcional.
- API: comprobación de salud real en `/api/health` y documentación en `/docs`.
- Web: portada parallax con carrusel enlazado y análisis separado con chat, tablas y gráficos.
- Datos: carga local verificada, 22.634 registros.
- Consultas: búsqueda, filtros, rankings, detalle, comparación y agregación por API.
- Conversación: reglas acotadas, selección de registros, recuperación e historial persistente.
- Interfaz de fase 6: versión inicial aprobada; mejoras y beta móvil pendientes.
- Modelo de IA: adaptador implementado; prueba real pendiente por créditos agotados. Continúa con advertencia y reglas locales.
- MCP: conectado a ChatGPT mediante túnel; metadatos y búsquedas reales comprobados. Casos completos de aceptación pendientes.

El CSV previsto es `anime_seasonal_20261116.csv` de LeoRigasaki/Anime-dataset.
Se consulta la copia identificada en la fase 3, sin necesitar Jikan ni el repositorio vecino.

## Preparación de datos (fase 3)

Desde la raíz del proyecto, sin necesitar acceso a Jikan:

```powershell
python scripts/prepare_dataset.py
python -m unittest discover -s scripts -p test_prepare_dataset.py -v
```

La entrada predeterminada es el CSV del repositorio vecino `../Anime-dataset`.
`data/processed/current.json` identifica una carga completa con copia original,
registros normalizados, informe de calidad y manifiesto. Repetir la preparación
con la misma entrada y transformación conserva la carga sin sobrescribirla.
La API resuelve ese puntero y verifica sus hashes. La carga se fija durante
la vida del proceso; reiniciar la API para incorporar una nueva carga preparada.

Ver [informe de calidad](docs/03-dataset.md) y [diccionario](docs/03-diccionario-datos.md).

## Requisitos

Python 3.11 o superior, Node.js 20.9 o superior y npm.
La validación completa de esta entrega utiliza Python 3.12 y Node 24;
las pruebas de imágenes usan soporte experimental para TypeScript de Node moderno.
Se usa venv/pip para Python y npm para la web. Trabajar desde esta carpeta.

## Instalar en PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .\apps\api
npm.cmd --prefix apps/web install
```

La primera instalación requiere conexión a los registros de paquetes.
`apps/web/package-lock.json` fija las dependencias de la web: para reinstalaciones
usar `npm.cmd --prefix apps/web ci`.
`apps/api/requirements-windows-py312.txt` registra las versiones Python instaladas
en Windows/Python 3.12; no es un bloqueo universal. Para reproducir ese entorno:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\apps\api\requirements-windows-py312.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .\apps\api
```

No ejecutar los recolectores de referencia.

## Ejecutar

Primera terminal, desde la raíz de `anime-data-agent`:

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py --mode rules
```

Segunda terminal, desde la misma carpeta:

```powershell
npm.cmd --prefix apps/web run dev
```

Abrir http://127.0.0.1:3000 para explorar y http://127.0.0.1:3000/analisis para conversar. También se puede
consultar http://127.0.0.1:8000/api/health o http://127.0.0.1:8000/docs.
Detener cada proceso con Ctrl+C. Si un puerto ya está ocupado, detener el proceso
propio que lo usa o elegir otro puerto y ajustar `API_URL` de forma coherente.

## Configuración

`.env.example` documenta las variables; no se carga automáticamente desde la raíz.
Por ejemplo, antes de arrancar Next.js:

```powershell
$env:API_URL = 'http://127.0.0.1:8000'
```

`ANIME_DATASET_PATH` y `ANIME_CONVERSATION_DB` admiten rutas absolutas o relativas
a la raíz del proyecto. El primero apunta a `data/processed/current.json`, no a
un JSON de registros sin manifiesto. El segundo guarda el historial SQLite.
El modo `rules` no necesita clave. El modo `openai` intenta usar la clave configurada solo en el backend;
si falta o el proveedor falla, continúa con reglas y advertencia.

## Modelo OpenAI (fase 7)

Crear la clave en https://platform.openai.com/api-keys y revisar saldo/créditos
del proyecto de API. No pegar la clave en el chat ni en archivos versionados.
Detener el Uvicorn anterior y ejecutar desde esta carpeta:

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py
```

La entrada de clave es oculta; el programa no la guarda en disco. El modelo
predeterminado configurable es `gpt-5-mini`. Arrancar el servidor no hace llamadas
al modelo; enviar mensajes sí puede generar consumo de API.

En otra terminal, para comprobar tres turnos reales con uso de API:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_model.py --allow-api
```

La prueba verifica filtros, contexto y comparación. El usuario la ejecutó, pero
OpenAI devolvió `credit_balance_exhausted`; no hay generación real aprobada. Luego recargar `/analisis` para ver el modo
y el consumo reportado por turno. Para volver a reglas sin modelo:

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py --mode rules
```

Si OpenAI no está disponible, se continúa con reglas locales y advertencia visible.
Enter sin clave también permite continuar. Reiniciar la API para reintentar el modelo. Ver límites,
datos enviados y presentación fundamentada en [fase 7](docs/07-modelo-ia.md).

## Probar consultas y conversación (fases 4 y 5)

Con la API reiniciada y la carga preparada:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_api.py
```

El comando comprueba las rutas por HTTP y crea una conversación de demostración.
Se pueden explorar los contratos en http://127.0.0.1:8000/docs.
Para ejecutar una demostración directa sin red y las pruebas:

```powershell
.\.venv\Scripts\python.exe scripts/demo_local.py
.\.venv\Scripts\python.exe -m unittest discover -s apps/api/tests -v
```

La suite usa el dataset real y bases temporales aisladas. El caso ASGI queda
omitido por defecto porque esta sesión no pudo ejecutar su bucle de eventos;
no equivale a HTTP aprobado. Ver evidencia y limitaciones en los documentos de fases 4 y 5.
Para incluirlo en un entorno que permita ejecutarlo: `$env:ANIME_HTTP_TESTS = '1'`.

## Comprobaciones

```powershell
npm.cmd --prefix apps/web run typecheck
npm.cmd --prefix apps/web run build
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:3000/api/health
```

La segunda consulta HTTP verifica el proxy de la web hacia la API.
El estado `ok` solo confirma que la API atiende; los demás campos declaran las
capacidades pendientes. Los resultados ejecutados se registran en `docs/02-proyecto.md`.

## Documentación y referencias

- [Plan](docs/00-plan.md).
- [Alcance detallado](docs/01-alcance.md).
- [Entrega de la fase 2](docs/02-proyecto.md).
- [Consultas, fase 4](docs/04-consultas.md).
- [Conversación e historial, fase 5](docs/05-conversacion.md).
- [Interfaz, fase 6](docs/06-interfaz.md).
- [Modelo de IA, fase 7](docs/07-modelo-ia.md).

## Imágenes y presentación

El tema sigue la preferencia claro/oscuro del navegador, con claro como respaldo.
La primera versión se dirige a escritorio; el diseño móvil se deja para beta.
Las imágenes son referencias externas opcionales, asociadas al mismo ID del anime;
si fallan, las fichas y consultas siguen funcionando. Para regenerar su índice:

```powershell
python scripts/prepare_media.py
```

El archivo auxiliar de AniList aporta solo imágenes; las estadísticas siguen
procediendo exclusivamente de la carga MyAnimeList validada. Ver condiciones,
cobertura visual y limitaciones en el documento de fase 6.
- Arquitectura de referencia: https://github.com/marcor0311/messi-wc-2022-data-agent
- Datos: https://github.com/LeoRigasaki/Anime-dataset

El código base de esta fase se escribió para anime; no se copiaron la galería,
imágenes, componentes deportivos ni credenciales del proyecto de referencia.


## Validación reproducible (fase 8)

Con las dependencias y la carga de datos ya preparadas:

```powershell
.\.venv\Scripts\python.exe scripts/validate_project.py
```

No llama a OpenAI. Ejecuta pruebas, seis casos de aceptación, demostración directa,
TypeScript y compilación. Guarda logs y resumen en `docs/evidence/phase8/`;
`latest.json` señala el último informe. Un resultado local correcto no acredita
una llamada real al modelo ni una prueba de navegador.

Para incluir HTTP, iniciar primero la API con reglas en otra terminal:

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py --mode rules
```

Y ejecutar `scripts/validate_project.py --http` con el Python del entorno virtual.
La prueba HTTP rechaza el modo OpenAI antes de enviar mensajes.
Ver [validación y limitaciones](docs/08-validacion.md) y
[recorrido de demostración](docs/08-demo.md).

Al clonar en otra máquina, `data/` no viene incluido: instalar dependencias,
obtener el CSV de la revisión indicada en `docs/03-dataset.md` y ejecutar
`prepare_dataset.py`. El chequeo de aceptación exige el hash acordado;
una nueva captura requiere revisar sus resultados esperados.


## MCP para ChatGPT (fase 9)

El servidor en `apps/mcp` expone búsqueda, ranking, detalle, comparación,
agregados y metadatos de la captura mediante herramientas de solo lectura.
Delega todos los cálculos a Python; no llama al modelo de la fase 7.

Con la API ya iniciada, desde la raíz:

```powershell
npm.cmd --prefix apps/mcp ci
npm.cmd --prefix apps/mcp run build
npm.cmd --prefix apps/mcp start
```

En otra terminal:

```powershell
npm.cmd --prefix apps/mcp run smoke
```

El endpoint privado es `http://127.0.0.1:3001/mcp`; no se pega localhost en
ChatGPT esperando acceso remoto directo. Para conectar esa cuenta, seguir la
[guía de fase 9](docs/09-mcp.md) con Secure MCP Tunnel. La conexión y consultas de metadatos y búsqueda desde ChatGPT se comprobaron;
falta completar los demás casos de aceptación. Ver también la
[guía paso a paso](docs/10-ejecucion-paso-a-paso.md).

`npm.cmd --prefix apps/mcp test` ejecuta diez pruebas de protocolo, contratos y
errores. `scripts/validate_project.py --http --mcp` añade esas pruebas al chequeo
general; requiere API local en reglas y no consume inferencia. El cliente smoke
también admite `--stdio`, o `--web` si la web está iniciada para contrastar su proxy.
