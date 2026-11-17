# Fase 3 — Preparación del dataset

Estado: aprobada explícitamente por el usuario. Posteriormente se autorizó
desarrollar las fases 4 y 5 conjuntamente. La integración de consultas se documenta
en `04-consultas.md`; los resultados siguientes corresponden al cierre de la fase 3.

## Trabajo realizado

Se creó `scripts/prepare_dataset.py` con biblioteca estándar de Python. Conserva
una copia exacta del CSV, normaliza registros, fija procedencia, produce un
informe de calidad y publica una carga local completa mediante un puntero atómico.
No se ejecutaron recolectores, no se llamó a Jikan y no se modificó el repositorio de origen.

La fase 2 fue aprobada explícitamente por el usuario antes de iniciar esta fase.

## Procedencia y reproducibilidad

| Dato | Valor |
| --- | --- |
| Repositorio | https://github.com/LeoRigasaki/Anime-dataset |
| Commit inspeccionado | `5d911e8eb286c0e8f17c263fb9ea7c09ceb1712c` |
| Archivo | `data/raw/anime_seasonal_20261116.csv` |
| Fecha declarada por nombre | 2026-11-16; no se conoce hora de extracción por fila. |
| SHA-256 CSV local | Ver manifiesto de la carga, preservado completo. |
| Fecha de referencia para futuros | 2026-11-16 |
| Fuente inicial | MyAnimeList v2 según el recolector `src/mal_api.py`. |

Se compararon los bytes del CSV con el archivo del commit, admitiendo solo la
conversión LF/CRLF de Git y registrando ambos hashes por separado. Cada carga
fija además el hash del script de transformación, tamaño original, hora UTC de
incorporación y hashes de los archivos generados. El ID de carga cambia si cambia
la entrada, transformación o fecha de referencia.

No se encontró archivo de licencia explícito en la raíz del repositorio inspeccionado.
Se registra esa limitación; esta fase prepara una copia local y no publica ni
autoriza redistribución pública del dataset. No se afirma que ausencia de licencia
sea una licencia abierta.

## Resultado de calidad

| Comprobación | Resultado |
| --- | ---: |
| Filas originales | 22.634 |
| Registros aceptados | 22.634 |
| Rechazados | 0 |
| Excluidos por alcance | 0 |
| IDs únicos | 22.634 |
| Sin puntuación publicada utilizable | 5.707 |
| Episodios desconocidos | 197 |
| Duración desconocida | 115 |
| Posición `rank` desconocida | 5.008 |
| Estudios ausentes | 7.450 |
| Géneros ausentes | 25 |
| Sinopsis ausentes tras recortar espacios | 1.944 |
| Fechas de inicio con precisión de mes | 445 |
| Fechas de inicio con precisión de año | 5 |
| Fechas de fin ausentes | 419 |
| Fechas de fin parciales | 531 |
| Inicios posteriores a referencia | 11 |

El conteo inicial de sinopsis vacías era 1.941; hay tres filas adicionales con
solo espacios. La normalización las registra como ausentes y conserva el texto original.
Todos los registros tienen al menos la advertencia de estadísticas no disponibles;
eso no convierte el registro completo en inválido.

| Formato | Registros |
| --- | ---: |
| TV | 6.254 |
| Películas | 3.249 |
| Música | 4.205 |
| ONA | 3.715 |
| OVA | 2.130 |
| Especiales | 1.528 |
| Especiales de TV | 769 |
| CM | 451 |
| PV | 332 |
| Desconocido | 1 |

La cobertura observada va de 1966 a 2026 y no certifica exhaustividad del catálogo
mundial ni de cada temporada. Todos los formatos se conservaron según lo aprobado.

## Decisiones de normalización aplicadas

- Se conservan IDs y las 29 columnas originales en `source_values`.
- Puntuación cero se trata como no publicada; se conservan sus valoraciones.
  Hay 5.700 títulos con puntuación cero y valoraciones mayores que cero: no se
  interpreta esa combinación como error que justifique borrar el título.
- Episodios, duración y posición `rank` iguales a cero se tratan como desconocidos.
- Las siete columnas de estadísticas de usuarios, todas en cero, quedan deshabilitadas
  y se expresan como null; no se atribuyen cero seguidores o favoritos reales.
- `popularity` conserva la posición de popularidad, distinta de conteo de seguidores.
- Se conservan fechas parciales sin inventar día o mes.
- `studios` y `genres` son listas, sin elementos vacíos o repetidos.
- No se exige mínimo de valoraciones para rankings; el mínimo seguirá siendo opcional.
- No se imputaron textos, estadísticas, nombres, traducciones o fechas con IA.

El [diccionario](03-diccionario-datos.md) detalla campos, unidades y restricciones.

## Archivos generados y regeneración

Dentro de `data/processed`, el puntero `current.json` identifica la carpeta activa.
Cada carpeta de carga contiene:

- `source.csv`: copia exacta original, funciona como capa raw de la carga.
- `anime.json`: registros normalizados ordenados por ID, con originales y advertencias.
- `quality.json`: conteos completos por año, formato y campos.
- `manifest.json`: procedencia y checksums.

Los datos están excluidos de Git según la configuración de la fase 2. La aplicación
usará su propia copia local y no dependerá del repositorio vecino al consultar.
El repositorio vecino solo es la entrada predeterminada para regenerar:

```powershell
python scripts/prepare_dataset.py
python -m unittest discover -s scripts -p test_prepare_dataset.py -v
```

Se pueden especificar `--source`, `--source-repo`, `--output` y `--reference-date`.
Si la entrada cambia de esquema, tiene IDs duplicados, valores inválidos o
estadísticas que contradicen la política actual, la preparación falla y exige
revisión. No actualiza el puntero vigente ni oculta descartes.

## Verificación ejecutada

- Cinco pruebas pasaron: fechas parciales e inválidas, ceros con valoraciones,
  estadísticas inesperadas, fecha futura incierta y protección del puntero frente
  a entrada inválida.
- Preparación completa sobre las 22.634 filas: sin rechazos ni duplicados.
- Segunda ejecución con la misma entrada y transformación: registros y puntero idénticos.
- Se comprobaron hashes de los archivos de carga y conservación del CSV original.
- No se probó la consulta desde la web: corresponde a fases posteriores.

## Revisión solicitada

Revisar las limitaciones y confirmar continuación a la fase 4. Las estadísticas
de seguidores, favoritos y estados de listas no podrán ofrecerse con esta carga;
sí se pueden preparar rankings por puntuación y por posición de popularidad.
Las advertencias no excluyen títulos del catálogo. No se necesita otra fuente para
seguir con las funciones sustentadas por esta carga.
