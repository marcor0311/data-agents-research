# Demostración de la entrega inicial

Desde la raíz del proyecto, con dependencias y dataset preparados, abrir dos terminales.

```powershell
.\.venv\Scripts\python.exe scripts/start_api.py --mode rules
```

```powershell
npm.cmd --prefix apps/web run dev
```

Abrir http://127.0.0.1:3000 y seleccionar una ficha: comprobar portada,
detalle y navegación hacia análisis. Las imágenes externas pueden faltar;
el catálogo y las cifras proceden de la carga local.

En http://127.0.0.1:3000/analisis, crear una conversación nueva:

| Acción | Mensaje o interacción | Qué comprobar |
| --- | --- | --- |
| Ranking | Muéstrame los 10 animes de fantasía mejor puntuados | 3.768 elegibles; tabla con puntuación y valoraciones. |
| Refinamiento | Solo series de televisión de máximo 26 episodios | 1.022 elegibles; se conserva fantasía y el orden. |
| Visualización | Cambiar tabla/gráfico | Mismos registros y valores. |
| Comparación | Seleccionar dos filas y escribir «Compara estos dos» | Dos IDs elegidos, con sus datos. |
| Consulta fuera de alcance | Solo TV y con doblaje costarricense | Pide aclarar; conserva resultado anterior. |
| Historial | Recuperar el primer turno | Vuelven filtros y ranking de ese turno. |
| Agregación | ¿Cuántas series se estrenaron por año desde 2020? | 1.731 registros, siete grupos de 2020 a 2026. |
| Procedencia | ¿Qué filtros aplicaste y de dónde vienen los datos? | Fuente, carga y parámetros aplicados. |
| Persistencia | Recargar la página | Recupera conversación y turno activo. |

Los valores esperados corresponden al CSV acordado, no al catálogo online actual.
Las temporadas y entregas son registros distintos. No se exige mínimo de votos;
los valores desconocidos se mantienen ausentes y los rankings informan omisiones.

Para mostrar continuidad sin IA, detener la API e iniciar `scripts/start_api.py`
sin `--mode rules`; presionar Enter sin clave. Enviar «Busca Death Note»:
debe mostrar advertencia y continuar localmente. No hace falta usar ni gastar una clave.
Una pregunta libre que exceda las reglas puede requerir reformularse.

Comprobación HTTP opcional, con API en reglas en puerto 8000:

```powershell
.\.venv\Scripts\python.exe scripts/smoke_api.py
```

Demostración directa sin navegador, sockets ni modelo:

```powershell
.\.venv\Scripts\python.exe scripts/demo_local.py
```

Esta última usa una base temporal; no borra ni modifica el historial del usuario.
