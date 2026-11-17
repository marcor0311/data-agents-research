# Fase 4 — Herramientas de consulta

Estado: verificadas como servicio y mediante HTTP real desde el equipo del usuario;
pendiente aprobación conjunta con la fase 5.
La fase 3 fue aprobada explícitamente; el usuario autorizó desarrollar 4 y 5 juntas.

## Implementación

- `models.py`: contratos tipados, límites y validación de filtros/consultas.
- `queries.py`: lector de carga, verificación de hashes, selección, orden y agregados.
- `main.py`: endpoints FastAPI con contratos OpenAPI.
- Configuración: `ANIME_DATASET_PATH` apunta ahora a `data/processed/current.json`.

La API sigue el puntero a la carga, verifica manifiesto, inventario y checksums de
los tres archivos, comprueba IDs y cantidad de registros. Mantiene esa carga fija
en memoria durante la vida del proceso. Para incorporar otra carga hay que reiniciar
la API; no se mezclan versiones a mitad de una consulta. No depende del repositorio
vecino ni de Jikan para consultar.

## Operaciones

| Operación | Entrada | Resultado |
| --- | --- | --- |
| Búsqueda | `kind=search`, filtro `title` | Candidatos por título principal, inglés y japonés; no selección automática. |
| Ranking | `kind=rank`, filtros, orden, dirección y límite | Filas, total elegible y cantidad omitida por métrica desconocida. |
| Detalle | `kind=detail`, un ID | Ficha con sinopsis y calidad disponible. |
| Comparación | `kind=compare`, dos IDs distintos | Mismas columnas para las dos entregas; valida filtros activos. |
| Agregación | `kind=aggregate`, `group_by=year/genre/studio` | Conteo sobre toda la selección; no solo los primeros resultados. |

## Filtros y orden

Filtros disponibles: título, formatos, géneros, estudio, año inicial/final de
estreno, estados, puntuación mínima, valoraciones mínimas opcionales y máximo
de episodios. Los nombres categóricos se validan contra `/api/dataset`.

Para varios géneros, la API exige `genre_mode=all` o `any`: no elige una preferencia
oculta. En las frases soportadas «y» representa todos y «o» cualquiera; una mezcla
ambigua pide aclaración. Estudio y géneros se comparan por etiqueta canónica.

Orden disponible: `score`, `popularity`, `scored_by`, `title`, `start_year`,
`episodes`, `duration_seconds`, `rank`. Por defecto puntuación descendente;
popularidad, posición rank y título ascendentes. Se puede indicar otra dirección.
Empates: ID ascendente. Límites: entre 1 y 100 filas. No hay mínimo obligatorio
de valoraciones. Las métricas deshabilitadas se rechazan por esquema.

Una métrica desconocida se omite al ordenar por ella y se informa su cantidad.
Los conteos agregados no exigen puntuación y conservan esos títulos. Al agrupar
por género/estudio, una obra puede contribuir a varios grupos: la suma no implica
obras distintas. Las listas vacías forman el grupo `Desconocido`.

## Contrato HTTP

| Método y ruta | Uso |
| --- | --- |
| `GET /api/health` | Vida de API; estado de carga validada o no disponible. |
| `GET /api/dataset` | Cobertura, vocabularios, métricas deshabilitadas y definiciones. |
| `POST /api/query` | Consulta tipada común para web, conversación y futuro MCP. |
| `GET /api/anime/search?title=Death%20Note` | Búsqueda por título. |
| `GET /api/anime/1535` | Ficha de Death Note según esta carga. |
| `GET /docs` | Interfaz OpenAPI para probar operaciones. |

Ejemplo de cuerpo de `POST /api/query`:

```json
{
  "kind": "rank",
  "filters": {"formats": ["tv"], "genres": ["Fantasy"], "max_episodes": 26},
  "order_by": "score",
  "limit": 10
}
```

Respuesta: `applied_query` canónica, `total`, `matched_total`,
`omitted_missing_metric`, `rows`, `groups`, `definitions` y `evidence`.
`total` es la selección elegible después de excluir valores desconocidos para
el orden; `matched_total` es el conteo filtrado anterior a esa exclusión.
La evidencia identifica carga, hashes, commit, parámetros efectivos, IDs seleccionados
y los IDs mostrados. No hay puntuaciones generadas por un modelo.

Errores: 422 para esquema/filtros inválidos; 404 para detalle inexistente;
503 para carga no verificable. Sin coincidencias: 200 y `status=empty`.

## Validación realizada

El ranking de fantasía, TV y máximo 26 episodios coincide con una lectura
independiente del CSV original: 1.022 elegibles con puntuación y 106 omitidos
por no tenerla, de 1.128 coincidencias iniciales. No se exigió mínimo de valoraciones.
Los totales corresponden a esta captura, no a la situación actual de MyAnimeList.

El agregado de TV por año desde 2020 reconcilia 1.731 registros y siete grupos,
incluso con `limit=1`. Se verificaron búsqueda vacía, comparación, filtros,
operadores de género, sentido de popularidad y métricas prohibidas.

Ver `apps/api/tests/test_queries_conversation.py`. La comprobación HTTP queda
separada: el bucle de eventos ASGI no finalizó en la sesión y se interrumpió.
No se registra como prueba aprobada; ejecutar `scripts/smoke_api.py` tras reiniciar
la API desde la terminal del usuario.

## Descripción para cierre

Se implementó el motor de consultas y su exposición HTTP, con resultados y
evidencia compartidos. Las verificaciones directas y la comprobación HTTP real
pasaron. Falta aprobación conjunta del usuario. No se inició fase 6.

## Resultado HTTP aportado por el usuario

El usuario ejecutó `scripts/smoke_api.py` y obtuvo:

```text
OK: dataset, ranking, validation, conversation, comparison, idempotency and history over real HTTP.
Records: 22634 | conversation: 69ab3f5c-ead1-4d93-9a1a-2f055c65bdd1
```

Esto verifica las rutas en ejecución y complementa las pruebas directas. La
prueba ASGI omitida en esta sesión continúa registrada como omitida: no se
confunde con esta comprobación HTTP distinta que sí pasó.
