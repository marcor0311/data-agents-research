import unittest
from unittest.mock import Mock, patch
from anime_agent.fallback import ResilientAgent
from anime_agent.models import AgentResponse, ConversationState
from anime_agent.openai_agent import ModelUnavailable


class FallbackTests(unittest.TestCase):
    def response(self):
        return AgentResponse(status='clarification', explanation='Reformulá la consulta.',
                             state=ConversationState(), visualization_action='retain')

    @patch('anime_agent.fallback.build_agent')
    def test_failure_continues_and_does_not_retry_provider(self, build):
        rules, model = Mock(), Mock()
        rules.invoke.side_effect = lambda work: {'response': self.response()}
        model.invoke.side_effect = ModelUnavailable('Créditos agotados.')
        build.side_effect = [rules, model]
        agent = ResilientAgent(object(), object())
        for _ in range(2):
            response = agent.invoke({'previous': None})['response']
            self.assertEqual(response.interpreter, 'bounded_rules')
            self.assertIn('Advertencia', response.explanation)
            self.assertIn('Créditos agotados', response.explanation)
        self.assertEqual(model.invoke.call_count, 1)

    @patch('anime_agent.fallback.build_agent')
    def test_missing_key_uses_rules(self, build):
        build.return_value.invoke.return_value = {'response': self.response()}
        agent = ResilientAgent(object(), warning='Falta la clave.')
        self.assertIn('Falta la clave', agent.invoke({})['response'].explanation)

    @patch('anime_agent.fallback.build_agent')
    def test_other_errors_are_not_hidden(self, build):
        build.side_effect = [Mock(), Mock()]
        agent = ResilientAgent(object(), object())
        agent.model.invoke.side_effect = ValueError('Invalid dataset')
        with self.assertRaises(ValueError):
            agent.invoke({})
