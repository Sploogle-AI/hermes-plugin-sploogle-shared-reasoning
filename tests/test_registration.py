"""Plugin entry-point contract without enabling it in any real profile."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RegistrationTests(unittest.TestCase):
    def test_registers_only_the_separate_explicit_async_tool_without_startup_io(self):
        path = ROOT / '__init__.py'
        self.assertTrue(path.exists(), 'Separate plugin entry point has not been implemented')
        spec = importlib.util.spec_from_file_location('sploogle_test_plugin', path, submodule_search_locations=[str(ROOT)])
        assert spec is not None and spec.loader is not None
        plugin = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = plugin
        spec.loader.exec_module(plugin)
        class Context:
            def __init__(self):
                self.tools = []
            def register_tool(self, **kwargs):
                self.tools.append(kwargs)
        ctx = Context()
        plugin.register(ctx)
        self.assertEqual(len(ctx.tools), 1)
        tool = ctx.tools[0]
        self.assertEqual(tool['name'], 'sploogle_shared_reasoning')
        self.assertTrue(tool['is_async'])
        self.assertFalse(tool.get('override', False))
        self.assertTrue(callable(tool['handler']))
        self.assertEqual(set(tool['schema']['parameters']['properties']), {'query', 'reasoning_level'})
        self.assertFalse(tool['schema']['parameters']['additionalProperties'])
        self.assertEqual(tool['schema']['parameters']['required'], ['query'])
        description = tool['schema']['description']
        self.assertIn('top-level', description)
        self.assertIn('generated', description)
        self.assertIn('recallMode', description)
        self.assertNotIn('sploogle_test_plugin.adapter', sys.modules)


if __name__ == '__main__':
    unittest.main()
