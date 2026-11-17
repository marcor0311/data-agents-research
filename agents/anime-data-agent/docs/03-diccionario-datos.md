# Diccionario de datos — carga normalizada v1

Un registro corresponde a un ID de MyAnimeList, no a una franquicia completa.
La transformación conserva las 29 columnas originales dentro de `source_values`.
Las listas normalizadas son arreglos; los textos vacíos se convierten en `null`.
El archivo `quality.json` de cada carga documenta sus valores ausentes y advertencias.

| Campo normalizado | Origen y significado | Tratamiento |
| --- | --- | --- |
| `anime_id` | ID de MyAnimeList | Entero positivo único; obligatorio. |
| `title` | Título principal | Texto obligatorio; conserva escritura. |
| `english_title` | Título en inglés | Texto o null. |
| `japanese_title` | Título en japonés | Texto o null. |
| `type` | Formato | Conserva código de origen; `unknown` no se infiere. |
| `episodes` | Episodios reportados | Entero positivo o null si cero/ausente. No significa episodios ya vistos o emitidos. |
| `duration_seconds` | `duration`, derivado de `average_episode_duration` | Segundos por episodio; cero → null. No es la duración de toda la serie. |
| `status` | Estado reportado | `finished_airing`, `currently_airing`, `not_yet_aired`. |
| `source` | Material original | Manga, novela, original y otros códigos; no es la procedencia del dataset. |
| `season` | Temporada declarada | Texto original; no reemplaza fecha de estreno. |
| `season_name`, `season_year` | Descomposición de `season` | Invierno/primavera/verano/otoño en códigos ingleses y año entero. |
| `studios` | Estudios | Arreglo separado desde `;`; [] significa desconocido, no ausencia real de estudio. |
| `genres` | Categorías de género de la fuente | Arreglo separado desde `;`; conserva etiquetas como Kids o Music. |
| `rating` | Clasificación de contenido de la fuente | Texto o null; no es puntuación del público. |
| `score` | Puntuación reportada | Número mayor que 0 y hasta 10; cero → null, nunca una reseña de cero puntos. |
| `scored_by` | Número de usuarios que puntuaron | Entero no negativo; se conserva aun si no hay score publicado. No exige mínimo por defecto. |
| `rank` | Posición de clasificación reportada por MAL | Entero positivo o null si cero. No equivale a un ranking recalculado por el agente. |
| `popularity` | Posición de popularidad de MAL | Entero positivo; menor posición indica mayor popularidad. No es cantidad de seguidores. |
| `members` | Supuesto número de usuarios en listas | No disponible: null por política de calidad. |
| `favorites` | Supuesto número de favoritos | No disponible: null por política de calidad. |
| `watching`, `completed`, `on_hold`, `dropped`, `plan_to_watch` | Supuestos conteos por estado de usuarios | No disponibles: null; no indican cero usuarios reales. |
| `start_date`, `end_date` | Fechas de inicio y fin | Conservan YYYY, YYYY-MM o YYYY-MM-DD; vacío → null. |
| `start_date_precision`, `end_date_precision` | Precisión de las fechas | `year`, `month`, `day` o null. No se agrega día ficticio. |
| `start_year` | Año de inicio | Derivado de la fecha, incluso si es parcial. |
| `future_start` | Inicio posterior a fecha de referencia | true, false o null si el intervalo de la fecha parcial no permite decidir. No sustituye `status`. |
| `broadcast_day`, `broadcast_time` | Emisión reportada | Texto o null; no afirma zona horaria ni programación vigente. |
| `synopsis` | Sinopsis disponible | Se recorta espacio externo; no se traduce, completa ni reescribe con IA. |
| `source_url` | Enlace a ficha de MyAnimeList | Construido a partir del ID; no implica validación web individual. |
| `quality_flags` | Razones de normalización/ausencia | Lista de advertencias por registro. |
| `source_values` | Las 29 columnas originales | Valores originales, incluidos los ceros, sin sobrescribir el CSV. |

## Estadísticas deshabilitadas

Las siete columnas `members`, `favorites`, `watching`, `completed`, `on_hold`,
`dropped` y `plan_to_watch` tienen cero en todas las filas. El recolector usa cero
por defecto para esos campos. No hay evidencia suficiente para interpretarlos
como conteos reales. Las herramientas de la fase 4 deben rechazar métricas basadas
en esas columnas; no se pueden generar rankings de seguidores o favoritos.
La posición `popularity` sí está presente y se puede usar con su definición explícita.

## Rankings y fechas

El agente ordenará la selección por el criterio solicitado, mostrando `scored_by`
al usar puntuación. No hay umbral obligatorio. Registros con `score=null` permanecen
en catálogo pero no tienen lugar en un ranking por puntuación. Los filtros
opcionales de mínimo de valoraciones se implementan en la fase 4.

Para determinar si una fecha parcial es futura se usan los límites del intervalo
solo de forma interna, sin publicarlos como fechas reales. La referencia inicial
es 2026-11-16 y queda fija en el manifiesto para poder reproducir el resultado.

## Identificación de una carga

`data/processed/current.json` apunta a un manifiesto mediante una ruta relativa y
su SHA-256. La carpeta de carga contiene `anime.json`, `source.csv`, `quality.json`
y `manifest.json`. Se incorpora una nueva carpeta completa antes de cambiar el
puntero; una entrada inválida no reemplaza la carga vigente. Las cargas previas
se conservan. No se carga automáticamente otro CSV por ser el más reciente.
