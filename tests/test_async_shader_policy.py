"""Compile the production SPH safety classifier and check non-skippable effects."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AsyncShaderPolicyTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'C compiler required')
    def test_writes_stream_output_and_non_graphics_stages_are_never_skippable(self):
        text = (ROOT/'games/totk/third_party/d2r_gfx/gfx/nvn/nvn_mtl.m').read_text()
        start = text.index('static int sph_keeps_memory(')
        end = text.index('\n}', start) + 2
        function = text[start:end]
        source = '#include <stdint.h>\n#include <string.h>\n#include <assert.h>\n' + function + r'''
int main(void) {
    uint8_t code[0x34] = {0};
    assert(!sph_keeps_memory(code, 0));
    assert(!sph_keeps_memory(code, 1));
    uint32_t global_store = 0x00010000;
    memcpy(code+0x30, &global_store, 4);
    assert(sph_keeps_memory(code, 0) && sph_keeps_memory(code, 1));
    for (int stream = 0; stream < 4; stream++) {
        uint32_t stream_out = UINT32_C(1) << (28+stream);
        memcpy(code+0x30, &stream_out, 4);
        assert(sph_keeps_memory(code, 0) && sph_keeps_memory(code, 1));
    }
    // Unrelated header fields must not force pure graphics stages to block.
    uint32_t unrelated = 0x0ffeffff;
    memcpy(code+0x30, &unrelated, 4);
    assert(!sph_keeps_memory(code, 0) && !sph_keeps_memory(code, 1));
    // Compute and unsupported stages must be retained even without header access.
    assert(sph_keeps_memory(NULL, 5));
    assert(sph_keeps_memory(NULL, 2));
    assert(sph_keeps_memory(NULL, 3));
    assert(sph_keeps_memory(NULL, 4));
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            cfile = Path(tmp)/'policy.c'
            binary = Path(tmp)/'policy'
            cfile.write_text(source)
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            str(cfile), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
