#!/usr/bin/env python3
"""Preprocessor API audit on Linux/macOS. This is NOT an Apple SDK compile."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GFX = ROOT / 'third_party/d2r_gfx/gfx'
INCLUDES = (GFX / 'nvn/include', GFX / 'nvn', ROOT / 'runtime')


def audit(backend):
    compiler = shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')
    if not compiler:
        raise RuntimeError('C preprocessor required')
    sources = sorted(GFX.rglob('*.m'))
    with tempfile.TemporaryDirectory(prefix='totk-metal-api-') as tmp:
        temp = Path(tmp)
        visited = set()

        def copy(path):
            path = path.resolve()
            if path in visited:
                return
            visited.add(path)
            content = path.read_text()
            for name in re.findall(r'^\s*#\s*(?:include|import)\s*"([^"]+)"', content, re.M):
                match = next((p for p in (path.parent / name, *(d / name for d in INCLUDES)) if p.is_file()), None)
                if match is None:
                    raise RuntimeError(f'{path}: unresolved local include {name}')
                copy(match)
            content = re.sub(r'^\s*#\s*(?:include|import)\s*<[^>]+>[^\n]*', '', content, flags=re.M)
            content = re.sub(r'^(\s*#\s*)import(\s+")', r'\1include\2', content, flags=re.M)
            out = temp / path.relative_to(ROOT)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content)

        for source in sources:
            copy(source)
        for source in sources:
            command = [compiler, '-E', '-x', 'c', f'-DDM_NVN_M3={int(backend == 3)}',
                       '-DTARGET_OS_OSX=1', '-DTARGET_OS_IPHONE=0', '-DTARGET_OS_SIMULATOR=0',
                       *(f'-I{temp / d.relative_to(ROOT)}' for d in INCLUDES), str(temp / source.relative_to(ROOT))]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode or result.stderr:
                raise RuntimeError(result.stderr)
            # Discard string literals (including diagnostics); only active code counts.
            code = re.sub(r'"(?:\\.|[^"\\])*"', '""', result.stdout)
            if backend == 3:
                bad = re.search(r'\b(?:MTL4\w*|MTLStage\w*|g_q4|newCommandAllocator\w*|newArgumentTableWithDescriptor|endCommandBuffer|beginCommandBufferWithAllocator)\b', code)
                if bad:
                    raise RuntimeError(f'{source.relative_to(ROOT)}: Metal 4 API in Metal 3 branch: {bad[0]}')
    return len(sources)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backend', type=int, choices=(3, 4), required=True)
    args = parser.parse_args()
    print(f'PASS: {audit(args.backend)} graphics translation units preprocessed for Metal {args.backend}; Apple SDK compilation still required')
