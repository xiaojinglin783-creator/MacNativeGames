from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import build_app


class PowerPolicyTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'C compiler required')
    def test_render_pacing_and_launcher_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp)/'power-policy'
            subprocess.run(['cc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                            '-I'+str(ROOT/'games/totk/app'),
                            '-I'+str(ROOT/'games/totk/third_party/d2r_gfx/gfx/nvn'),
                            str(ROOT/'tests/power_policy_probe.c'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_launcher_knows_the_selected_backend(self):
        for backend, target, macro in (('3', '15.0', '1'), ('4', '26.0', '0')):
            with tempfile.TemporaryDirectory() as tmp:
                tree = Path(tmp)
                (tree/'build').mkdir()
                (tree/'build/AppIcon.icns').touch()
                with patch.object(build_app, 'run') as run:
                    build_app.step_binary(tree, 'unused.nsp', 'unused.keys',
                                          {'METAL_BACKEND': backend, 'MACOSX_DEPLOYMENT_TARGET': target}, tree/'logs')
                launcher = next(c.args[0] for c in run.call_args_list if 'app/launcher.m' in c.args[0])
                self.assertIn('-DDM_NVN_M3='+macro, launcher)
                self.assertIn('-mmacosx-version-min='+target, launcher)
