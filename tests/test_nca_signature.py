"""Exercise real RSA verification with synthetic headers; no firmware/console keys."""
from pathlib import Path
import sys
import unittest
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'games/totk/scripts'))
from verify_nca_signature import verify_nca_header_signature


class NcaSignatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.moduli = (private.public_key().public_numbers().n.to_bytes(256, 'big'),)
        header = bytearray(0xc00)
        header[0x200:0x204] = b'NCA3'
        header[0x205] = 4
        header[:0x100] = private.sign(bytes(header[0x200:0x400]), padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
        cls.header = bytes(header)

    def test_valid_signature(self):
        verify_nca_header_signature(self.header, self.moduli)

    def test_modified_signed_header_is_rejected(self):
        header = bytearray(self.header)
        header[0x280] ^= 1  # FS header hashes are covered by the signature.
        with self.assertRaisesRegex(ValueError, 'signature verification failed'):
            verify_nca_header_signature(bytes(header), self.moduli)

    def test_unknown_generation_and_truncation_are_rejected(self):
        header = bytearray(self.header)
        header[0x221] = 2
        for data in (bytes(header), self.header[:-1], bytes(0xc00)):
            with self.assertRaises(ValueError):
                verify_nca_header_signature(data, self.moduli)

    def test_synthetic_signature_is_not_a_retail_signature(self):
        with self.assertRaisesRegex(ValueError, 'signature verification failed'):
            verify_nca_header_signature(self.header)
