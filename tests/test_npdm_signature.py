"""Synthetic signed metadata only: no game files or private console keys."""
import importlib.util
from pathlib import Path
import struct
import unittest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
import build_app

path = Path(__file__).resolve().parents[1] / 'games/totk/scripts/verify_npdm_signature.py'
spec = importlib.util.spec_from_file_location('npdm_signature', path)
npdm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(npdm)


class NpdmSignatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.modulus = private.public_key().public_numbers().n.to_bytes(256, 'big')
        data = bytearray(0x300)
        data[:4] = b'META'
        struct.pack_into('<IIII', data, 0x70, 0x2c0, 0x40, 0x80, 0x240)
        data[0x2c0:0x2c4] = b'ACI0'
        struct.pack_into('<Q', data, 0x2d0, npdm.TITLE_ID)
        data[0x180:0x280] = cls.modulus
        data[0x280:0x284] = b'ACID'
        struct.pack_into('<I', data, 0x284, 0x140)
        data[0x80:0x180] = private.sign(bytes(data[0x180:0x2c0]), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
        cls.data = bytes(data)

    def test_valid_signature(self):
        npdm.verify(self.data, self.modulus)

    def test_tampered_signed_payload_is_rejected(self):
        data = bytearray(self.data)
        data[0x28c] ^= 1
        with self.assertRaises(InvalidSignature):
            npdm.verify(bytes(data), self.modulus)

    def test_wrong_title_and_bounds_rejected(self):
        for offset, value in ((0x2d0, 0), (0x74, 0xfffffff0), (0x78, 0), (0x284, 0xfffffff0)):
            data = bytearray(self.data)
            struct.pack_into('<I', data, offset, value)
            with self.assertRaises(ValueError):
                npdm.verify(bytes(data), self.modulus)

    def test_wrong_public_root_rejected(self):
        with self.assertRaises(InvalidSignature):
            npdm.verify(self.data)

    def test_variant_is_limited_to_base_npdm(self):
        digest = build_app.VERIFIED_BASE_NPDM
        self.assertTrue(build_app.exefs_hash_matches('v0', 'main.npdm', digest, 'reference'))
        for version, name in (('v143', 'main.npdm'), ('v0', 'main'), ('v0', 'sdk')):
            self.assertFalse(build_app.exefs_hash_matches(version, name, digest, 'reference'))
        self.assertFalse(build_app.exefs_hash_matches('v0', 'main.npdm', 'e78c40978c23b42866973e6fe506c2ad7716ec51c651f35bfeada3415bb3b634', 'reference'))
