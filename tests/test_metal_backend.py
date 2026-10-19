from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import build_app

ROOT = Path(__file__).resolve().parents[1]


class MetalBackendTests(unittest.TestCase):
    def test_automatic_os_boundaries(self):
        for major in (15, 16, 25):
            self.assertEqual(build_app.metal_backend(major), '3')
        for major in (26, 27):
            self.assertEqual(build_app.metal_backend(major), '4')
        with self.assertRaises(build_app.BuildError):
            build_app.metal_backend(14)

    def test_explicit_backend_respects_os(self):
        self.assertEqual(build_app.metal_backend(26, '3'), '3')
        with self.assertRaisesRegex(build_app.BuildError, 'Metal 4 requires'):
            build_app.metal_backend(15, '4')

    def test_make_uses_separate_objects_and_targets(self):
        for api, minimum, macro in ((3, '15.0', 1), (4, '26.0', 0)):
            result = subprocess.run(['make', '-Bn', f'METAL_BACKEND={api}', 'check-metal'], cwd=ROOT / 'games/totk', capture_output=True, text=True, check=True)
            self.assertIn(f'build/gfx-metal{api}/', result.stdout)
            self.assertIn(f'-mmacosx-version-min={minimum}', result.stdout)
            self.assertIn(f'-DDM_NVN_M3={macro}', result.stdout)
            self.assertNotIn('frontend_ios.m', result.stdout)

    def test_shader_cache_is_recompiled_for_older_deployment(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            seed = tree / 'build/shader-seed/v0'
            seed.mkdir(parents=True)
            (seed / 'a.metal').write_text('kernel void test() {}')
            invocations = []

            def compile_shader(command, **kwargs):
                invocations.append(command)
                Path(command[command.index('-o') + 1]).write_bytes(b'test-metallib')
                return SimpleNamespace(returncode=0, stdout='', stderr='')

            with patch.object(build_app, 'metal_compiler', return_value=('metal', 'test compiler', {})), patch.object(build_app.subprocess, 'run', side_effect=compile_shader):
                build_app.step_shader_libs(tree, tree / 'logs', deployment_target='26.0')
                build_app.step_shader_libs(tree, tree / 'logs', deployment_target='26.0')
                self.assertEqual(len(invocations), 1)
                build_app.step_shader_libs(tree, tree / 'logs', deployment_target='15.0')
                self.assertEqual(len(invocations), 2)
                self.assertIn('-mmacosx-version-min=15.0', invocations[-1])

    def test_active_api_branches(self):
        for api in (3, 4):
            subprocess.run([sys.executable, str(ROOT / 'games/totk/scripts/check_metal_api.py'), '--backend', str(api)], check=True)
