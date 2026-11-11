"""Native resolver delegation; fixtures here are unit-only."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_adapter():
    entry = ROOT / '__init__.py'
    spec = importlib.util.spec_from_file_location('sploogle_adapter_test', entry, submodule_search_locations=[str(ROOT)])
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    assert (ROOT / 'adapter.py').exists(), 'Native profile adapter has not been implemented'
    from importlib import import_module
    return import_module(spec.name + '.adapter')


class AdapterTests(unittest.TestCase):
    def test_delegates_profile_resolution_each_call_without_reimplementing_host_precedence(self):
        adapter = load_adapter()
        configs = iter([SimpleNamespace(base_url='http://one.invalid/v3', workspace_id='one', peer_name='OwnerOne', api_key='unit-key-one', timeout=20, enabled=True), SimpleNamespace(base_url='http://two.invalid', workspace_id='two', peer_name='OwnerTwo', api_key='unit-key-two', timeout=30, enabled=True)])
        calls = []
        def importer(name, submodule):
            calls.append((name, submodule))
            return SimpleNamespace(HonchoClientConfig=SimpleNamespace(from_global_config=lambda: next(configs)))
        reader = lambda: {'memory': {'provider': 'honcho'}}
        first = adapter.resolve_connection(config_reader=reader, module_importer=importer)
        second = adapter.resolve_connection(config_reader=reader, module_importer=importer)
        self.assertEqual(first.workspace, 'one')
        self.assertEqual(first.base_url, 'http://one.invalid')
        self.assertEqual(first.human_peer, 'OwnerOne')
        self.assertEqual(second.workspace, 'two')
        self.assertEqual(second.api_key, 'unit-key-two')
        self.assertEqual(calls, [('honcho', 'client'), ('honcho', 'client')])
    def test_refuses_inactive_or_disabled_honcho_before_importing_provider(self):
        adapter = load_adapter()
        for config in [{}, {'memory': {'provider': 'other'}}, {'memory': {'provider': 'honcho'}, 'plugins': {'disabled': ['honcho']}}, {'memory': {'provider': 'honcho'}, 'plugins': {'disabled': ['memory/honcho']}}]:
            calls = []
            def importer(*args):
                calls.append(args)
                self.fail('Inactive provider was imported')
            with self.subTest(config=config):
                with self.assertRaises(ValueError):
                    adapter.resolve_connection(config_reader=lambda: config, module_importer=importer)
                self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
