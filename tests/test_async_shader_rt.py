"""Run the production Objective-C translation queue with an isolated fake service."""
from pathlib import Path
import os
import platform
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'games/totk'


@unittest.skipUnless(platform.system() == 'Darwin', 'Apple Foundation and SDK required')
class AsyncShaderRuntimeTests(unittest.TestCase):
    def test_background_jobs_publish_only_after_hook_and_share_cache(self):
        with tempfile.TemporaryDirectory(prefix='totk-async-test-') as tmp:
            tree = Path(tmp)
            service = tree / 'build/shader-service/totk_xlate'
            service.parent.mkdir(parents=True)
            service.write_text('#!' + sys.executable + '\n' + r'''
import json, pathlib, signal, sys, time
out = pathlib.Path(sys.argv[sys.argv.index('--out')+1])
assert signal.SIGCHLD not in signal.pthread_sigmask(signal.SIG_BLOCK, [])
for line in sys.stdin:
    q = json.loads(line)
    code = pathlib.Path(q['code']).read_bytes()
    assert len(code) == 0x50  # copied by the worker, before service execution
    time.sleep(0.025)
    key = q['variant']
    (out / (key+'_b.metal')).write_text('// synthetic test shader\n')
    (out / (key+'_b.json')).write_text(json.dumps({'deps': {k:q[k] for k in ('tex','img','attr','fout')}}))
    print(json.dumps({'ok':True}), flush=True)
''')
            service.chmod(0o755)
            binary = tree / 'build/probe'
            gfx = GAME / 'third_party/d2r_gfx/gfx/nvn'
            subprocess.run(['xcrun', 'clang', '-arch', 'arm64', '-mmacosx-version-min=15.0',
                            '-DDM_NVN_M3=1', '-fobjc-arc', '-fblocks', '-Wno-deprecated-declarations',
                            '-I'+str(GAME/'runtime'), '-I'+str(gfx), '-I'+str(gfx/'include'),
                            str(GAME/'tests/async_shaders/probe.m'), str(gfx/'totk_shader_rt.m'),
                            '-framework', 'Foundation', '-o', str(binary)], check=True, timeout=120)
            env = os.environ.copy()
            for name in ('TOTK_SHADER_XLATE', 'TOTK_SHADER_CONTRIB'):
                env.pop(name, None)
            env.update(TOTK_SHADER_CACHE=str(tree/'cache'), TOTK_SHADER_SEED='off',
                       TOTK_SHADER_SERVICE='native', TOTK_SHADER_NO_TRANSLATE='0',
                       TOTK_RT_BG_WORKERS='2', TOTK_RT_URGENT_WORKERS='2')
            result = subprocess.run([str(binary)], env=env, cwd=tree, text=True,
                                    capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('PASS: production async shader queues', result.stdout)
