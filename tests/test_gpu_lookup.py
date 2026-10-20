from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GpuLookupTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('cc'), 'C compiler required')
    def test_sorted_lookup_boundaries_and_registry_mutations(self):
        source = r'''
#include <assert.h>
#include <limits.h>
#include "nvn_gpu_lookup.h"
typedef struct { uint64_t gpu, length, identity; } record;
int main(void) {
    record rows[512]; size_t count = 0;
    uint64_t seed = 1234567;
    assert(nvn_gpu_upper_bound(NULL, 0, sizeof(record), 0) == 0);
    for (size_t iteration = 0; iteration < 20000; iteration++) {
        seed = seed * 6364136223846793005ULL + 1;
        if (count && ((seed >> 32) & 1 || count == 512)) {
            size_t at = (seed >> 33) % count;
            memmove(rows + at, rows + at + 1, (--count - at) * sizeof(record));
        } else {
            uint64_t address = iteration % 17 == 0 ? UINT64_MAX : (seed >> 32) % 100;
            size_t at = nvn_gpu_upper_bound(rows, count, sizeof(record), address);
            memmove(rows + at + 1, rows + at, (count - at) * sizeof(record));
            rows[at] = (record){address, 16, iteration}; count++;
        }
        for (size_t i = 1; i < count; i++) assert(rows[i-1].gpu <= rows[i].gpu);
        for (size_t q = 0; q < 104; q++) {
            uint64_t address = q == 103 ? UINT64_MAX : q;
            size_t reference = 0;
            while (reference < count && rows[reference].gpu <= address) reference++;
            assert(nvn_gpu_upper_bound(rows, count, sizeof(record), address) == reference);
        }
    }
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            cfile = Path(tmp) / 'probe.c'
            binary = Path(tmp) / 'probe'
            cfile.write_text(source)
            include = ROOT / 'games/totk/third_party/d2r_gfx/gfx/nvn'
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-I', str(include), str(cfile), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
