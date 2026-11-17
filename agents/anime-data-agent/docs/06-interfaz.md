# Fase 6 — Interfaz

Estado: versión inicial aprobada explícitamente por el usuario para la entrega
y el prototipo funcional. Mejoras visuales y beta móvil quedan pendientes para
iteraciones posteriores. La aprobación no se presenta como validación automatizada
de los aspectos que esta sesión no pudo comprobar en navegador.
Las fases 4 y 5 fueron aprobadas antes de iniciar esta fase.

## Decisiones confirmadas

- Portada `/` y espacio de análisis `/analisis` en páginas separadas.
- La portada tendrá una lista de animes enlazada con una ficha grande.
- Elegir un anime actualiza conjuntamente imagen, fondo y datos de la ficha.
- La experiencia del proyecto de Messi es una referencia, sin copiar su identidad deportiva.
- Parallax y carrusel/slide moderno, con controles explícitos de selección.
- Tema según preferencia claro/oscuro que expone el navegador (`prefers-color-scheme`).
  Si no se expresa preferencia oscura, el respaldo es claro. No se modifica el tema del sistema.
- Primera versión para computadora; diseño móvil se pospone a una beta de mejoramiento.

## Propuesta funcional para concretar

- Portada: lista seleccionable, ficha con título, atributos y sinopsis disponible,
  imagen y fondo asociados al mismo ID del catálogo.
- Acción para llevar el anime seleccionado al análisis mediante su ID validado.
- Análisis: conversación con resultados, tabla, gráficos, detalle y selección de
  dos registros para comparar; conservar filtros y evidencia de las fases 4 y 5.
- La clasificación destacada debe indicar métrica y fecha de captura; no se
  presentará como ranking actual en tiempo real.
- Imagen ausente o fallida: respaldo legible con título y datos, sin inventar
  una imagen ni mostrar la portada de otro anime.

## Decisiones visuales para revisión

- Se conserva el nombre técnico Anime Data Agent hasta que el usuario elija otro.
- Paleta propuesta: superficies neutras y acento oliva en claro, con acento suave
  de contraste en oscuro. Es una propuesta revisable, no una preferencia atribuida al usuario.
- Selección manual por tarjetas o flechas; no hay rotación automática que interrumpa
  lectura. El fondo entra suavemente y responde al scroll con parallax.
- Cada ID puede tener portada y un banner; no se inventan wallpapers adicionales.

## Implementación realizada

### Portada `/`

- Cabecera con navegación a explorar y análisis.
- Fondo parallax y ficha principal con título, sinopsis y métricas reales.
- Portada superpuesta, etiquetas, enlace de atribución de imagen y acción de análisis.
- Tres selecciones de hasta 20 títulos mediante el motor de consultas existente:
  estrenos 2025–2026 por puntuación, mejor puntuados del catálogo y posición de popularidad.
- Búsqueda explícita por título; escribir no dispara consultas en cada tecla.
- Carrusel horizontal de tarjetas, selección sincronizada por ID, botones anterior/siguiente.
- Estado de carga, resultado vacío, error con reintento y conservación de selección previa.
- Fecha de captura visible; no se presentan datos como popularidad actual en vivo.

### Análisis `/analisis`

- Dos paneles: conversación a la izquierda y resultados a la derecha.
- Conexión real con los endpoints de fases 4/5; ninguna respuesta de chat simulada.
- Se conserva en localStorage el ID de conversación; los turnos viven en SQLite.
- Historial visible con recuperación de un turno y continuación desde ese contexto.
- Botón de nueva conversación que conserva las anteriores en el backend.
- Mensajes con Enter o botón; Shift+Enter conserva salto de línea.
- Sugerencias de frases acotadas; se indica que el modelo de IA sigue pendiente.
- Tabla y gráfico de barras construidos a partir del mismo objeto de resultado.
- Selección de hasta dos registros, comparación con filtros conservados y fichas detalladas.
- Agregados por grupo, explicación de multiplicidad y evidencia expandible.
- Los refinamientos conservan resultados hasta recibir la respuesta completa.
- Reintento de envío conserva exactamente el cuerpo y `request_id`; si se perdió
  la respuesta después de guardar, la API devuelve el turno existente sin duplicarlo.
- Si el turno base está desactualizado, se recupera historial antes de un nuevo envío.
- Un anime elegido en portada llega por ID en URL y se muestra como sugerencia
  «Ver en la conversación»; no altera automáticamente el historial anterior.

### Tema y accesibilidad

- Tema mediante CSS, sin parpadeo de alternancia por hidratación ni selector que
  sobreescriba la preferencia del usuario.
- `prefers-reduced-motion` desactiva parallax, transiciones y scroll suave.
- Controles con etiquetas, foco visible, encabezados, tablas con caption y estados
  anunciados. Las barras incluyen texto numérico y los valores desconocidos se distinguen.
- No se cambió la configuración de accesibilidad o tema del equipo para probarlos.
- Hay un respaldo legible para pantallas estrechas; no se declara soporte móvil
  validado. La beta móvil queda pendiente según la decisión del usuario.

## Imágenes y procedencia

El CSV estadístico sigue siendo la única fuente de puntuación y datos analíticos.
`scripts/prepare_media.py` lee únicamente IDs y enlaces visuales del CSV auxiliar
`anilist_seasonal_20261115.csv`, enlaza por MAL ID existente y produce
`apps/web/public/media-index.json`. No importa puntuaciones de AniList ni llama
a su API. Registra archivo, commit, SHA-256 y fecha de recopilación de las referencias.

Esta descripción corresponde al índice inicial. La corrección posterior añade
una consulta visual bajo demanda, documentada al final de este archivo.

Se obtuvieron 723 IDs coincidentes y 434 banners. Las cifras previas de 903/509
eran disponibilidad en el archivo auxiliar antes de exigir correspondencia con
el catálogo principal y resolver duplicados. Las referencias no dan cobertura
de imagen a todos los clásicos.

Las imágenes se cargan desde los hosts de AniList registrados, sin descargarlas
masivamente ni copiarlas como archivos locales. Un banner ausente usa la portada
del mismo ID como fondo; si falla o no existe, se muestra un respaldo gráfico
neutro. Nunca se sustituye por la imagen de otro anime. Se enlaza la ficha de origen.
El índice visual se ignora si su carga no coincide con el dataset usado en pantalla.

Se consultaron las condiciones publicadas en
https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/terms-of-use
que diferencian uso educativo y recolección masiva de API. El proyecto no invoca
esa API para imágenes. No se atribuye una licencia de artwork al dataset: los
enlaces son referencias externas y no una autorización de redistribución comercial.

## Archivos principales

| Archivo/grupo | Función |
| --- | --- |
| `src/components/explore.tsx` | Portada, selección, búsqueda y parallax. |
| `src/components/analysis.tsx` | Conversación, historial, tabla, gráfico y detalle. |
| `src/components/shared.tsx` | Navegación, imágenes con respaldo, métricas y ficha. |
| `src/lib/api.ts` | Contratos y llamadas al proxy de API; formato de valores. |
| `src/app/page.tsx`, `src/app/analisis/page.tsx` | Rutas separadas. |
| `src/app/globals.css` | Tema automático, disposición y movimiento reducido. |
| `public/media-index.json` | Referencias de imágenes por ID; sin estadísticas. |
| `scripts/prepare_media.py` | Regeneración reproducible del índice visual. |

## Verificación y bloqueos

- `npm.cmd --prefix apps/web run typecheck`: correcto.
- `npm.cmd --prefix apps/web run build`: correcto; genera `/` y `/analisis`.
- Índice visual generado desde el catálogo local: 723 IDs, 434 banners.
- La revisión visual automatizada no pudo realizarse: el navegador integrado
  rechazó asociar la pestaña a la sesión; el control de Chrome detuvo la operación
  porque no pudo identificar con suficiente confianza su URL activa.
- No se atribuye a esa revisión ninguna captura ni resultado de navegación.
- Falta comprobar en navegador el aspecto a 1440×900 y 1920×1080, imágenes,
  selección del carrusel, contraste en ambos temas, reducción de movimiento,
  navegación al análisis y conversación completa con comparación e historial.
- La API y su prueba HTTP aprobada en fases 4/5 se reutilizan. La interfaz nueva
  todavía no se declara validada de extremo a extremo.

## Cómo revisar

Mantener la API activa. Si la web está en modo desarrollo, recargar
http://127.0.0.1:3000. Si estaba detenida, ejecutar desde el proyecto:

```powershell
npm.cmd --prefix apps/web run dev
```

1. Elegir una tarjeta distinta; comprobar cambio conjunto de título, ficha y fondo.
2. Probar las tres selecciones y búsqueda `Death Note` (puede no tener imagen).
3. Abrir «Analizar este anime» y pulsar «Ver en la conversación».
4. Pedir «Muéstrame los 10 animes de fantasía mejor puntuados» y luego «Solo TV».
5. Seleccionar dos filas y comparar; alternar tabla/gráfico y recuperar un turno anterior.
6. Recargar análisis y comprobar el historial; detener API para revisar error y reintento.

## Descripción de cierre provisional

Se implementaron las dos páginas y sus conexiones a datos, consultas y conversación,
con parallax, carrusel y tema automático según lo acordado. La compilación pasó.
Falta la revisión visual y funcional en navegador y la aprobación del usuario.
No se inició la fase 7 ni se afirma que haya un modelo de IA conectado.

## Corrección tras la primera revisión del usuario

El usuario reportó muchas tarjetas sin imagen y que el clic no mostraba el detalle.
Se identificaron dos causas: cobertura visual limitada a 723 IDs y selección que
solo actualizaba el hero fuera de la zona visible. Además, los fallos al descargar
la ficha se ocultaban.

Cambios aplicados:

- El clic en una tarjeta abre un diálogo nativo con ficha completa, sinopsis,
  métricas, fuentes y botones de análisis y regreso a la ficha de portada.
- La ficha informa carga o error y ofrece reintento, sin declarar ausente una
  sinopsis que aún se está descargando. Escape o el botón de cierre cierran el diálogo.
- El hero sigue actualizándose por el mismo ID; se evita mezclar un detalle previo
  con la portada del nuevo ID seleccionado.
- `POST /api/artwork` es una ruta de Next.js que consulta referencias visuales de
  AniList para los IDs visibles, en lotes de hasta 20, con caché de 24 horas en
  memoria. No descarga el catálogo ni importa puntuaciones o estadísticas.
- La respuesta exige coincidencia exacta de `idMal`; solo se admiten hosts de
  imágenes permitidos. Una respuesta ajena a ese ID nunca se utiliza.
- El índice local queda como respaldo. La portada muestra un aviso y reintento
  si la fuente externa no está disponible; los datos analíticos no dependen de ella.
- Las consultas visuales ocurren desde el servidor Next.js al navegar, por lo
  que requieren conexión del equipo a `graphql.anilist.co` y a sus hosts de imágenes.
  No se garantiza cobertura completa ni disponibilidad de todas las portadas.

Verificación: cuatro pruebas de la ruta pasaron con respuestas de proveedor
controladas: validación de IDs, asociación exacta y caché, rechazo de ID distinto,
fallo del proveedor y descarte de hosts ajenos. Son pruebas simuladas de ese
adaptador, no evidencia de acceso real a AniList desde esta sesión.
La revisión visual sigue pendiente del usuario por la limitación de control de navegador.
