#!/usr/bin/env python3
"""Read small instruction windows from a local rewritten module; never execute it."""
import argparse
from pathlib import Path
import struct


def instruction_window(path, offset):
    size = path.stat().st_size
    if offset < 0 or offset % 4 or offset + 4 > size:
        raise ValueError(f'offset {offset:#x} is not an aligned instruction in the image')
    start = max(0, offset - 24)
    length = min(52, (size - start) // 4 * 4)
    with path.open('rb') as stream:
        stream.seek(start)
        return start, stream.read(length)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', type=Path, required=True)
    parser.add_argument('--offset', type=lambda text: int(text, 0), action='append', required=True)
    args = parser.parse_args()
    try:
        from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM
        decoder = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
    except ImportError:
        decoder = None
    try:
        for offset in args.offset:
            start, data = instruction_window(args.image, offset)
            print(f'--- main+{offset:#x} (read-only instruction context) ---')
            # Decode each word separately so an invalid encoding cannot hide
            # the requested instruction by stopping a multi-instruction decode.
            for index, (word,) in enumerate(struct.iter_unpack('<I', data)):
                address = start + 4 * index
                insn = next(decoder.disasm(data[4*index:4*index+4], address), None) if decoder else None
                assembly = f'{insn.mnemonic} {insn.op_str}' if insn else '(raw instruction)'
                marker = '>>' if address == offset else '  '
                print(f'{marker} {address:08x}: {word:08x}  {assembly}')
    except (OSError, ValueError) as error:
        parser.exit(1, f'Cannot read instruction context: {error}\n')


if __name__ == '__main__':
    main()
