#!/usr/bin/env python3
"""Verify a base-game NPDM variant's retail ACID signature and bounded layout.

Public verification modulus: SciresM/hactool (MIT), pki.c, retail ACID key 0,
commit 1d64a83450e025622f3468c28fc4164dad2c5ef6. No decryption/private keys.
"""
import argparse
import hashlib
from pathlib import Path
import struct
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

RETAIL_ACID_MODULUS = bytes.fromhex(
    "ddc8ddf24e6df0ca9ec75dc77badfe7d238969b6f206a20288e15591abcb4d50"
    "2efc9d9476d64cd8ff10fa5e930ab457ac51c71666f41a54c2c5043d1bfe3020"
    "8aac6f6ff5c7b668b8c9406b42ad1121e78be9750186e4489b0a0af87fe887f2"
    "8201e6a30fe466ae833f4e9f5e0130a400b99aae5f03cc1860e5ef3b5e1516fe"
    "1c8278b52f477c0666885d35a2672010e76c4368d3e45a682a5ae26d73b03153"
    "1c200944f51a9d22be12a17711e2a1cd409aa28b609befa0d34863a2f8a32c08"
    "56522e6019675aa79fdc3f3f692b316ab7884a148480333c9d44b73f4ce175ea"
    "37eae81e7c77b7c61aa2f09f1061cd7b5b324c37efb17168530aed517d3522fd"
)
BASE_NPDM_SHA256 = '890c6174a31605519d82361fd5e2e941d684601f6aec317caa67b7e1a60b0c5a'
TITLE_ID = 0x0100F2C0115B6000


def verify(data, modulus=RETAIL_ACID_MODULUS):
    if len(data) < 0x80 or data[:4] != b'META':
        raise ValueError('invalid NPDM header')
    if struct.unpack_from('<I', data, 4)[0] != 0:
        raise ValueError('unsupported ACID signing key index')
    aci, aci_size, acid, acid_size = struct.unpack_from('<IIII', data, 0x70)
    for start, size, minimum in ((aci, aci_size, 0x40), (acid, acid_size, 0x240)):
        if start < 0x80 or size < minimum or start + size > len(data):
            raise ValueError('NPDM section out of bounds')
    if not (aci + aci_size <= acid or acid + acid_size <= aci):
        raise ValueError('overlapping NPDM sections')
    if data[aci:aci+4] != b'ACI0' or data[acid+0x200:acid+0x204] != b'ACID':
        raise ValueError('invalid ACI0/ACID magic')
    if struct.unpack_from('<Q', data, aci+0x10)[0] != TITLE_ID:
        raise ValueError('unexpected game program ID')
    signed_size = struct.unpack_from('<I', data, acid+0x204)[0]
    if signed_size < 0x140 or signed_size + 0x100 != acid_size:
        raise ValueError('invalid ACID signed size')
    for start, size, base, minimum in ((aci, aci_size, 0, 0x40), (acid, acid_size, 0x200, 0x240)):
        for field in (0x20, 0x28, 0x30):
            offset, length = struct.unpack_from('<II', data, start+base+field)
            if length and (offset < minimum or offset + length > size):
                raise ValueError('NPDM permission section out of bounds')
    key = rsa.RSAPublicNumbers(65537, int.from_bytes(modulus, 'big')).public_key()
    key.verify(data[acid:acid+0x100], data[acid+0x100:acid+acid_size],
               padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('npdm', type=Path)
    args = parser.parse_args()
    try:
        data = args.npdm.read_bytes()
        if hashlib.sha256(data).hexdigest() != BASE_NPDM_SHA256:
            raise ValueError('not the reviewed base-game NPDM variant')
        verify(data)
    except (ValueError, InvalidSignature, OSError) as error:
        parser.exit(1, f'NPDM verification failed: {error or "invalid retail signature"}\n')
    print('PASS: reviewed 1.0.0 NPDM SHA-256, title ID, section bounds and retail ACID signature')
