"""Continue locally after an unavailable model, without retrying paid calls."""
import threading

from anime_agent.conversation import build_agent
from anime_agent.openai_agent import ModelUnavailable


class ResilientAgent:
    def __init__(self, repository, interpreter=None, warning=None):
        self.rules = build_agent(repository)
        self.model = build_agent(repository, interpreter) if interpreter else None
        self.warning = warning
        self.lock = threading.Lock()

    def invoke(self, work):
        # Serialize the transition so subsequent turns do not retry a failed provider.
        with self.lock:
            if self.model is not None and not self.warning:
                try:
                    return self.model.invoke(work)
                except ModelUnavailable as error:
                    self.warning = str(error)
            response = self.rules.invoke(work)['response']
            if self.warning:
                response = response.model_copy(update={
                    'explanation': 'Advertencia: no se pudo conectar con la IA. '
                    + self.warning + ' Continuamos con reglas locales; se admiten consultas acotadas. '
                    + response.explanation,
                })
            return {'response': response}
