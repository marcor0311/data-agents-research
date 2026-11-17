"""Bounded Spanish interpreter. Unsupported wording is clarified, never guessed."""
import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from anime_agent.models import AgentResponse, ConversationState, Filters, Query, TurnRequest
from anime_agent.queries import InvalidQuery, norm

GENRE_ES = {'accion': 'Action', 'aventura': 'Adventure', 'fantasia': 'Fantasy',
            'comedia': 'Comedy', 'drama': 'Drama', 'romance': 'Romance', 'terror': 'Horror',
            'misterio': 'Mystery', 'deportes': 'Sports', 'ciencia ficcion': 'Sci-Fi',
            'suspenso': 'Suspense', 'musica': 'Music', 'infantil': 'Kids'}


class Clarify(ValueError):
    pass


def named_id(repo, title):
    exact = [r['anime_id'] for r in repo.records if any(norm(title) == norm(r.get(k) or '')
             for k in ('title', 'english_title', 'japanese_title'))]
    if len(exact) != 1:
        raise Clarify('No hay un único título exacto. Buscalo primero y usá los IDs de la entrega que querés comparar.')
    return exact[0]


def resolve(repo, previous, request):
    state = previous.state.model_copy(deep=True) if previous else ConversationState()
    if state.load_id is not None and state.load_id != repo.load_id:
        raise Clarify('La carga de datos cambió. Iniciá una conversación nueva para no mezclar versiones; el resultado anterior se conserva.')
    visible = {r['anime_id'] for r in previous.result.rows} if previous and previous.result else set()
    if request.selected_ids is not None:
        if len(set(request.selected_ids)) != len(request.selected_ids) or not set(request.selected_ids) <= visible:
            raise Clarify('Seleccioná IDs distintos que aparezcan en el resultado activo de esta conversación.')
        state.selected_ids = request.selected_ids
    text = norm(request.message.strip()).rstrip('.?!¿¡').strip()
    if text.startswith('¿'):
        text = text[1:]
    if text in ('que filtros aplicaste y de donde vienen los datos', 'que filtros aplicaste', 'de donde vienen los datos'):
        if not previous or not previous.result:
            raise Clarify('Primero realizá una consulta para ver su fuente y filtros.')
        return state, 'explain'
    if text in ('estos dos', 'compara estos dos', 'comparalos'):
        if not state.query or len(state.selected_ids) != 2:
            raise Clarify('Seleccioná dos IDs del resultado activo para comparar estos dos.')
        q = state.query.model_copy(deep=True)
        q.kind, q.ids = 'compare', state.selected_ids[:]
    elif text in ('ese anime', 'detalle de ese anime', 'muestrame ese anime'):
        if not state.query or len(state.selected_ids) != 1:
            raise Clarify('Seleccioná un único anime del resultado activo.')
        q = state.query.model_copy(deep=True)
        q.kind, q.ids = 'detail', state.selected_ids[:]
    elif match := re.fullmatch(r'(?:busca|buscar) (.+)', text):
        q = Query(kind='search', filters=Filters(title=match[1]), order_by='title')
    elif match := re.fullmatch(r'(?:detalle|muestrame el detalle) (?:del? )?(?:id )?(\d+)', text):
        q = Query(kind='detail', ids=[int(match[1])])
    elif match := re.fullmatch(r'compara (\d+) (?:con|y) (\d+)', text):
        q = Query(kind='compare', ids=[int(match[1]), int(match[2])])
    elif match := re.fullmatch(r'compara (.+) con (.+)', text):
        q = Query(kind='compare', ids=[named_id(repo, match[1]), named_id(repo, match[2])])
    elif match := re.fullmatch(r'(?:muestrame |dame )?(?:los )?(\d+) animes(?: de (.+?))? (?:mejor puntuados|con mayor puntuacion)', text):
        genres, mode = [], None
        if match[2]:
            phrase = match[2]
            if ' y ' in phrase and ' o ' in phrase:
                raise Clarify('Indicá solo géneros unidos por «y» (todos) o por «o» (cualquiera).')
            mode = 'any' if ' o ' in phrase else 'all'
            for word in re.split(r' [yo] ', phrase):
                genre = GENRE_ES.get(word, next((g for g in repo.genres if norm(g) == word), None))
                if not genre:
                    raise Clarify('Género no reconocido. Consultá los géneros disponibles.')
                genres.append(genre)
        q = Query(filters=Filters(genres=genres, genre_mode=mode), limit=int(match[1]))
    elif match := re.fullmatch(r'cuantas (series|animes) se estrenaron por ano desde (\d{4})', text):
        q = Query(kind='aggregate', filters=Filters(formats=['tv'] if match[1] == 'series' else [], year_from=int(match[2])), group_by='year')
    else:
        if not state.query:
            raise Clarify('Probá «Busca Death Note» o «Muéstrame los 10 animes de fantasía mejor puntuados».')
        q = state.query.model_copy(deep=True)
        if match := re.fullmatch(r'solo (?:series de television|tv)(?: de maximo (\d+) episodios)?', text):
            q.filters.formats = ['tv']
            if match[1]:
                q.filters.max_episodes = int(match[1])
        elif match := re.fullmatch(r'(?:solo (?:los )?de |de )?maximo (\d+) episodios', text):
            q.filters.max_episodes = int(match[1])
        elif match := re.fullmatch(r'(?:solo )?(?:desde|a partir de) (\d{4})', text):
            q.filters.year_from = int(match[1])
        elif match := re.fullmatch(r'(?:solo )?(?:con )?(?:un )?minimo (?:de )?(\d+) valoraciones', text):
            q.filters.min_votes = int(match[1])
        elif text == 'sin minimo de valoraciones':
            q.filters.min_votes = None
        elif text == 'sin limite de episodios':
            q.filters.max_episodes = None
        elif text == 'todos los formatos':
            q.filters.formats = []
        elif match := re.fullmatch(r'ordena(?:los)? por (puntuacion|popularidad|valoraciones|titulo)(?: (ascendente|descendente))?', text):
            if q.kind in ('compare', 'detail', 'aggregate'):
                raise Clarify('El orden se aplica a una búsqueda o ranking; recuperá ese turno primero.')
            q.order_by = {'puntuacion': 'score', 'popularidad': 'popularity', 'valoraciones': 'scored_by', 'titulo': 'title'}[match[1]]
            q.direction = {'ascendente': 'asc', 'descendente': 'desc'}.get(match[2])
        else:
            raise Clarify('Esa condición todavía no está implementada en el intérprete acotado. El resultado anterior se conserva; no se aplicó parcialmente el mensaje.')
    # Revalidate mutations, including constraints bypassed by assignment.
    q = Query.model_validate(q.model_dump())
    state.query, state.load_id = q, repo.load_id
    return state, 'query'


class Work(TypedDict, total=False):
    previous: AgentResponse | None
    request: TurnRequest
    state: ConversationState
    action: str
    clarification: str
    result: object
    response: AgentResponse


def build_agent(repo, model_interpreter=None):
    def interpret(work):
        if model_interpreter is not None:
            return {'response': model_interpreter.run(work.get('previous'), work['request'])}
        try:
            state, action = resolve(repo, work.get('previous'), work['request'])
            return {'state': state, 'action': action}
        except ValueError as error:
            # Pydantic errors and unsupported/ambiguous requests do not mutate state.
            return {'clarification': str(error) if isinstance(error, Clarify) else 'Parámetros fuera del alcance o límites admitidos; reformulá la consulta.'}

    def query(work):
        if work.get('clarification') or work.get('action') == 'explain':
            return {}
        try:
            result = repo.execute(work['state'].query)
            state = work['state'].model_copy(deep=True)
            state.query = result.applied_query
            visible = {r['anime_id'] for r in result.rows}
            state.selected_ids = [i for i in state.selected_ids if i in visible]
            return {'result': result, 'state': state}
        except InvalidQuery as error:
            return {'clarification': str(error)}

    def compose(work):
        previous = work.get('previous')
        if work.get('clarification'):
            response = AgentResponse(status='clarification', explanation=work['clarification'],
                       state=previous.state if previous else ConversationState(),
                       result=previous.result if previous else None, visualization_action='retain')
        elif work['action'] == 'explain':
            r = previous.result
            response = AgentResponse(status='result', state=work['state'], result=r, visualization_action='retain',
                explanation=f"Fuente: MyAnimeList mediante LeoRigasaki/Anime-dataset. Carga {r.evidence['load_id']}. Filtros y orden: {r.applied_query.model_dump_json()}. La fecha del archivo no certifica actualización por fila.")
        else:
            r = work['result']
            explanation = (f'{r.total} registros agrupados en {len(r.groups)} grupos.' if r.kind == 'aggregate'
                           else f'{r.total} registros elegibles; se muestran {len(r.rows)}.')
            if r.omitted_missing_metric:
                explanation += f' {r.omitted_missing_metric} sin dato para ordenar.'
            explanation += ' Datos de la captura local; intérprete de reglas acotadas, sin modelo de IA.'
            response = AgentResponse(status=r.status, explanation=explanation, state=work['state'], result=r,
                       visualization_action='update' if previous and previous.result else 'create')
        return {'response': response}

    graph = StateGraph(Work)
    graph.add_node('resolve', interpret)
    graph.add_node('query', query)
    graph.add_node('compose', compose)
    graph.add_edge(START, 'resolve')
    graph.add_conditional_edges('resolve', lambda work: END if work.get('response') is not None else 'query', {END: END, 'query': 'query'})
    graph.add_edge('query', 'compose')
    graph.add_edge('compose', END)
    return graph.compile()
