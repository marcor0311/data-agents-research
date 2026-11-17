# Fase 2 — Estructura del proyecto

Estado: aprobada explícitamente por el usuario tras verificar conexión, desconexión y recuperación.
La fase 3 no se ha iniciado. No se considera esta fase completada aún.

## Qué se hizo

- Se cerró la fase 1 con catálogo completo y mínimo de valoraciones opcional.
- Se crearon `apps/api` (FastAPI/Python), `apps/web` (Next.js/TypeScript) y
  `apps/mcp` (reserva documental para Node.js/TypeScript en fase 9).
- LangGraph está declarado como dependencia; no se creó un grafo de ejemplo que
  pudiera confundirse con una conversación ya implementada.
- La API expone `/api/health` con capacidades pendientes explícitas y `/docs`.
- La web consulta la salud por el proxy `/api/health` con estados de espera,
  conexión fallida y reintento. Es una pantalla técnica provisional.
- Se configuran rutas del dataset e historial; todavía no se leen ni se escriben.
- Se agregaron README, variables de ejemplo y exclusiones de Git para datos,
  credenciales, dependencias y archivos generados.
- Se detectó un repositorio Git propio ya existente. No se cambió su remoto,
  no se creó otro y no se hicieron commits ni publicaciones.
- No se modificaron los dos repositorios de referencia ni el CSV original.

## Archivos principales

| Grupo | Finalidad |
| --- | --- |
| `apps/api/pyproject.toml` | Dependencias y empaquetado del backend. |
| `apps/api/src/anime_agent/config.py` | Rutas configurables desde la raíz del proyecto. |
| `apps/api/src/anime_agent/main.py` | API base y estado de infraestructura. |
| `apps/web/package.json`, `tsconfig.json`, `next.config.ts` | Dependencias, TypeScript y proxy hacia la API. |
| `apps/web/src/app/` | Página provisional de conexión y estilos mínimos. |
| `apps/mcp/README.md` | Reserva de alcance; no es un MCP funcional. |
| `.env.example`, `.gitignore`, `README.md` | Configuración, exclusiones y arranque en PowerShell. |

## Verificación ejecutada

Entorno observado: Python 3.12.4, Node.js 24.21.0 y npm 11.19.0.

| Comprobación | Resultado |
| --- | --- |
| Sintaxis de los módulos Python nuevos | Correcta, mediante análisis AST. |
| Lectura JSON de package.json y tsconfig.json | Correcta. |
| Raíz del proyecto y rutas predeterminadas | Correctas mediante ejecución del módulo de configuración. |
| Ruta de dataset configurable por variable | Correcta. |
| Creación del entorno con `python -m venv .venv` | Correcta. |
| Instalación Python | Falló: no se resuelve `pypi.org`. |
| Instalación npm | Falló: no se resuelve `registry.npmjs.org`. |
| Instalación npm offline | Falló: paquetes ausentes en caché. |
| Arranque API/web, typecheck y build | No ejecutables aún por dependencias ausentes. |
| Comprobación real del proxy web → API | Pendiente; no se simularon respuestas. |

La primera creación con uv falló al escribir su caché; se probó una ubicación
temporal permitida y se observó además el bloqueo DNS. Se adoptó `python -m venv`
en las instrucciones. No se cambió DNS, proxy ni la configuración de seguridad del equipo.

## Pendientes para cerrar la fase

Actualización tras instalación del usuario: se verificó que FastAPI 0.163.1,
Uvicorn, LangGraph y `anime_agent.main` se importan correctamente desde `.venv`.
La instalación del backend ya está disponible. No existen aún
`apps/web/node_modules/next/package.json` ni `apps/web/package-lock.json`.
Se intentó comprobar HTTP local en el puerto 18000, pero la sesión rechazó el
acceso al socket por permisos. No se considera verificado el arranque HTTP.
El aviso de actualización de pip es informativo y no requiere actualizarlo.

Desde una terminal con acceso a PyPI y npm, ejecutar desde `anime-data-agent`:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .\apps\api
npm.cmd --prefix apps/web install
```

Después ejecutar los dos servidores y comprobaciones del README. Con instalación
real se deben generar y revisar `package-lock.json` y un archivo de bloqueo para
Python; no se inventaron versiones resueltas o hashes de paquetes sin descargarlos.
Para un bloqueo Python multiplataforma se puede usar `uv pip compile --universal`
sobre `apps/api/pyproject.toml` cuando exista acceso a los registros.

Antes de aprobar esta fase faltan:

1. Instalar dependencias y fijar versiones resueltas reproducibles.
2. Verificar `/api/health` directamente y a través del proxy web.
3. Ejecutar comprobación TypeScript y compilación web.
4. Revisar pantalla de conexión y error con API detenida.
5. Presentar evidencia y recibir revisión del usuario.

## Límites del resultado

## Verificación posterior a la instalación del usuario

- El usuario instaló la web con `npm.cmd`: 27 paquetes, auditoría reportada sin vulnerabilidades.
- `npm.cmd --prefix apps/web run typecheck`: código de salida 0.
- `npm.cmd --prefix apps/web run build`: código de salida 0; Next.js 16.4.6,
  compilación y generación de páginas correctas.
- Next.js añadió `allowJs` a tsconfig y actualizó sus referencias de tipos.
- Ejecución directa del manejador de salud y generación OpenAPI: correctas.
  Esto no equivale a una comprobación HTTP ni del proxy.
- La comprobación ASGI en proceso no terminó en esta sesión y se interrumpió;
  no se considera aprobada. El acceso TCP de la sesión ya había sido rechazado.
- Existe `package-lock.json`. Se registraron las versiones instaladas de Python
  en `apps/api/requirements-windows-py312.txt` (Windows/Python 3.12, no universal).
- Se actualizaron los comandos a `npm.cmd` para PowerShell sin cambiar su política.

El historial de intentos anterior explica los bloqueos iniciales. Ya no es
necesario repetir la instalación. Para cerrar faltan abrir API y web desde la
terminal del usuario, comprobar conexión, respuesta del proxy y estado de error
al detener la API; después revisar la fase. La fase 3 sigue pendiente.

### Funcionalidad todavía pendiente

## Evidencia de ejecución informada por el usuario

El usuario ejecutó API y web y compartió el contenido de la página local:
«API conectada correctamente». También aparecen dataset pendiente de integrar,
conversación pendiente, modelo sin conectar y MCP pendiente, tal como corresponde
a esta fase. Esto confirma el recorrido navegador → proxy Next.js → API FastAPI.
La comprobación fue informada por el usuario; no se atribuye a una inspección
automatizada del navegador desde esta sesión.

El usuario también confirmó las dos comprobaciones restantes:

1. Al detener la API y comprobar conexión, la página mostró «No se pudo comprobar
   la API. Verificá que esté ejecutándose y volvé a intentar».
2. Al volver a iniciar la API y comprobar conexión, mostró «API conectada correctamente»
   y los estados pendientes de dataset, conversación, modelo y MCP.

El recorrido conexión → desconexión → recuperación queda verificado por evidencia
aportada por el usuario. No se observaron cambios necesarios para corregir ese recorrido.

## Descripción de cierre para revisión

Se preparó la estructura base de backend y web, configuración de rutas, proxy,
dependencias, documentación de arranque y pantalla provisional de salud. TypeScript
y build pasaron; el usuario verificó la conexión y su recuperación tras detener
y reiniciar la API. Se registraron versiones instaladas y bloqueos iniciales sin
ocultarlos ni atribuirles fallos del producto. No se implementaron funciones de
fases posteriores. La fase 2 está lista para aprobación del usuario y la fase 3
permanece sin iniciar.

Esta fase no incorpora dataset, consultas de anime, historial funcional, chat,
modelo de IA ni herramientas MCP. El estado saludable de API no representa
disponibilidad de esas funciones. La interfaz final requiere revisión en fase 6.
