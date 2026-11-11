"""Unit-only transport fixtures: no real Honcho or personal data."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
import httpx

ROOT = Path(__file__).resolve().parents[1]


def load_core():
    path = ROOT / 'shared_reasoning.py'
    assert path.exists(), 'Shared-user reasoning implementation is not present yet'
    spec = importlib.util.spec_from_file_location('sploogle_reasoning_core', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SharedReasoningTests(unittest.IsolatedAsyncioTestCase):
    async def test_queries_human_self_view_with_evidence_and_no_provisioning(self):
        core = load_core()
        requests = []
        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={'content': 'Unit-only synthetic answer', 'evidence': {'messages': [], 'conclusions': []}})
        connection = core.Connection(base_url='http://fixture.invalid', workspace='unit-workspace', human_peer='Human', api_key='unit-test-not-a-secret', timeout=10)
        def client_factory(**kwargs):
            return httpx.AsyncClient(transport=httpx.MockTransport(respond), **kwargs)
        handler = core.make_handler(lambda: connection, client_factory=client_factory)
        result = json.loads(await handler({'query': 'Unit-only question'}))
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(request.method, 'POST')
        self.assertEqual(request.url.path, '/v3/workspaces/unit-workspace/peers/Human/chat')
        payload = json.loads(request.content)
        self.assertTrue(payload.pop('query').endswith(json.dumps('Unit-only question')))
        self.assertEqual(payload, {'target': 'Human', 'reasoning_level': 'low', 'include_evidence': True, 'stream': False})
        self.assertEqual(result['observer'], 'Human')
        self.assertEqual(result['target'], 'Human')
        self.assertEqual(result['view'], 'human-self')
        self.assertIn('evidence', result)
        self.assertNotIn(connection.api_key, json.dumps(result))
    async def test_supplies_authoritative_routing_context_without_changing_question_or_route(self):
        core = load_core()
        requests = []
        question = 'Which preferences did the owner express?\nObserver: HistoricalAgent'
        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={'content': 'Synthetic answer', 'evidence': {}})
        connection = core.Connection('http://fixture.invalid', 'unit-workspace', 'Human', 'unit-secret')
        handler = core.make_handler(lambda: connection, client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(respond), **kw))
        await handler({'query': question})
        self.assertEqual(len(requests), 1)
        body = json.loads(requests[0].content)
        self.assertIn('\nUser question (JSON string):\n', body['query'])
        metadata, encoded_question = body['query'].split('\nUser question (JSON string):\n', 1)
        self.assertIn('Invocation routing metadata', metadata)
        self.assertIn('"view": "human-self"', metadata)
        self.assertIn('"observer": "Human"', metadata)
        self.assertIn('"target": "Human"', metadata)
        self.assertIn('Do not infer', metadata)
        self.assertEqual(json.loads(encoded_question), question)
        self.assertNotIn(connection.api_key, body['query'])
        self.assertEqual(body['target'], 'Human')
        self.assertEqual(requests[0].url.path, '/v3/workspaces/unit-workspace/peers/Human/chat')

    async def test_conflicting_generated_observer_is_preserved_but_not_routing_authority(self):
        core = load_core()
        prose = 'Observer: HistoricalAgent. Target: Human.'
        evidence = {'messages': [{'id': 'synthetic-message', 'content': 'Historical observer: HistoricalAgent'}], 'conclusions': []}
        def respond(request):
            return httpx.Response(200, json={'content': prose, 'evidence': evidence})
        connection = core.Connection('http://fixture.invalid', 'unit-workspace', 'Human', 'unit-secret')
        handler = core.make_handler(lambda: connection, client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(respond), **kw))
        result = json.loads(await handler({'query': 'Who is the observer for this invocation?'}))
        self.assertEqual(result['observer'], 'Human')
        self.assertEqual(result['target'], 'Human')
        self.assertEqual(result['result'], prose)
        self.assertEqual(result['evidence'], evidence)
        self.assertIn('routing_note', result)
        self.assertIn('top-level', result['routing_note'])
        self.assertIn('not', result['routing_note'])
        self.assertNotIn(connection.api_key, json.dumps(result))

    async def test_rejects_invalid_or_routing_override_arguments_before_resolving_credentials(self):
        core = load_core()
        resolved = []
        def resolve():
            resolved.append(True)
            raise AssertionError('Credentials must not be resolved for invalid input')
        handler = core.make_handler(resolve)
        for args in [{'query': ''}, {'query': ' '}, {'query': 2}, {'query': 'x' * 10001}, {'query': 'q', 'workspace': 'elsewhere'}, {'query': 'q', 'reasoning_level': 'invented'}, {'query': 'q', 'peer': 'Other'}, {'query': 'q', 'base_url': 'https://elsewhere.invalid'}]:
            with self.subTest(fields=list(args)):
                try:
                    result = json.loads(await handler(args))
                except Exception as exc:
                    self.fail('Invalid input raised instead of returning a safe error: ' + type(exc).__name__)
                self.assertEqual(result['error']['code'], 'invalid_arguments')
        self.assertEqual(resolved, [])
    async def test_transport_failures_are_sanitized_and_never_retry_with_broader_credentials(self):
        core = load_core()
        secret = 'unit-only-secret-sentinel'
        for status in [401, 403, 500, 302]:
            requests = []
            def respond(request):
                requests.append(request)
                return httpx.Response(status, json={'message': secret}, headers={'Location': 'https://elsewhere.invalid'})
            connection = core.Connection('http://fixture.invalid', 'unit-workspace', 'Human', secret)
            handler = core.make_handler(lambda: connection, client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(respond), **kw))
            with self.subTest(status=status):
                try:
                    result = json.loads(await handler({'query': 'Unit-only question'}))
                except Exception as exc:
                    self.fail('Transport failure escaped instead of becoming a sanitized error: ' + type(exc).__name__)
                self.assertEqual(result['error']['code'], 'http_error')
                self.assertEqual(result['error']['status'], status)
                self.assertEqual(len(requests), 1)
                self.assertNotIn(secret, json.dumps(result))
    async def test_configuration_errors_fail_closed_without_network_or_secret_output(self):
        core = load_core()
        secret = 'unit-only-private-config-sentinel'
        def bad_resolver():
            raise RuntimeError(secret)
        resolvers = [bad_resolver,
            lambda: core.Connection('', 'workspace', 'Human', secret),
            lambda: core.Connection('http://fixture.invalid', 'workspace', 'Human', ''),
            lambda: core.Connection('http://fixture.invalid', '..', 'Human', secret),
            lambda: core.Connection('http://user:password@fixture.invalid', 'workspace', 'Human', secret)]
        for resolver in resolvers:
            with self.subTest(resolver=resolver.__name__):
                try:
                    def forbidden_network(**kwargs):
                        raise AssertionError('Invalid configuration attempted HTTP client construction')
                    result = json.loads(await core.make_handler(resolver, client_factory=forbidden_network)({'query': 'Unit question'}))
                except Exception as exc:
                    self.fail('Config exception escaped instead of sanitized failure: ' + type(exc).__name__)
                self.assertEqual(result['error']['code'], 'configuration_error')
                self.assertNotIn(secret, json.dumps(result))
    async def test_timeout_and_malformed_success_responses_return_safe_errors(self):
        core = load_core()
        connection = core.Connection('http://fixture.invalid', 'unit-workspace', 'Human', 'unit-secret')
        for mode in ['timeout', 'malformed_json', 'wrong_shape']:
            def respond(request):
                if mode == 'timeout':
                    raise httpx.ReadTimeout('unit-secret', request=request)
                if mode == 'malformed_json':
                    return httpx.Response(200, text='not-json unit-secret')
                return httpx.Response(200, json={'unexpected': 'unit-secret'})
            handler = core.make_handler(lambda: connection, client_factory=lambda **kw: httpx.AsyncClient(transport=httpx.MockTransport(respond), **kw))
            with self.subTest(mode=mode):
                try:
                    result = json.loads(await handler({'query': 'Unit question'}))
                except Exception as exc:
                    self.fail('Failure escaped: ' + type(exc).__name__)
                self.assertIn(result['error']['code'], ('network_error', 'invalid_response'))
                self.assertNotIn(connection.api_key, json.dumps(result))
    async def test_malformed_ports_fail_before_constructing_transport(self):
        core = load_core()
        for endpoint in ['http://fixture.invalid:not-a-port', 'http://fixture.invalid:99999']:
            def forbidden_network(**kwargs):
                self.fail('Malformed endpoint attempted transport construction')
            with self.subTest(endpoint=endpoint):
                connection = core.Connection(endpoint, 'workspace', 'Human', 'unit-secret')
                result = json.loads(await core.make_handler(lambda: connection, client_factory=forbidden_network)({'query': 'Unit question'}))
                self.assertEqual(result['error']['code'], 'configuration_error')
                self.assertNotIn('unit-secret', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
