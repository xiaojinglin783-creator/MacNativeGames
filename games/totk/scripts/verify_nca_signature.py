"""Public retail NCA header signature verification (no decryption keys).

Public verification moduli: SciresM/hactool (MIT), pki.c nca_keys_retail,
commit 1d64a83450e025622f3468c28fc4164dad2c5ef6. Header signature coverage:
nca.c nca_process: RSA-PSS-SHA256 over header[0x200:0x400].
"""
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

RETAIL_NCA_MODULI = (
    bytes.fromhex(
        "bfbe406cf4a780e9f07d0c99611d772f96bc4b9e58381b03abb175499f2b4d58"
        "34b005a37522be1a3f0373ac7068d116b904465eb707912f078b26def60007b2"
        "b451f80d0a5e58adebbc9ad649b964efa782b5cf6d7013b00f85f6a908aa4d67"
        "6687fa89ff7590181e6b3de98a68c92604d980ce3f5e92ce01ff063bf2c1a90c"
        "ce026f16bc92420a4164cd52b6344daec02edea4df27683cc1a060ad43f3fc86"
        "c13e6c46f77c299ffafdf0e3ce64e735f2f656566f6df1e242b08340a5c3202b"
        "cc9aaecaed4d7030a8701c70fd1363290279ead2a7af3528321c7be62f1aaa40"
        "7e328c2742fe8278ec0debe6834b6d8104401a9e9a67f67229fa04f09de4f403"
    ),
    bytes.fromhex(
        "ade3e1fa0435e5b6dd49ea8929b1ffb643dfca96a04a13df43d9949796436548"
        "705833a27d357b96745e0b5c32181424c258b36c227aa1b7cb90a7a3f97d4516"
        "a5c8ed8fad395e9e4b51687df80c35c63f91ae44a592300d46f840ffd0ff06d2"
        "1c7f9618dcb71d663ed173bc158a2f94f300c183f1cdd78188abdf8cef97dd1b"
        "175f58f69ae9e8c22f3815f52107f837905d2e024024150d25b7265d09cc4cf4"
        "f21b94705a9eeeed7777d45199f5dc761ee36c8cd112d457d1b683e4e4fedae9"
        "b43b33e5378adfb57f89f19b9eb015b23afeea61845b7d4b23120b8312f2226b"
        "b922964b260b635e965752a3676422cad0563e74b5981f0df8b334e698685aad"
    ),
)


def verify_nca_header_signature(header, moduli=RETAIL_NCA_MODULI):
    if len(header) != 0xc00 or header[0x200:0x204] != b'NCA3':
        raise ValueError('invalid NCA3 header')
    generation = header[0x221]
    if generation >= len(moduli):
        raise ValueError(f'unsupported retail NCA signature key generation {generation}')
    key = rsa.RSAPublicNumbers(65537, int.from_bytes(moduli[generation], 'big')).public_key()
    try:
        key.verify(header[:0x100], header[0x200:0x400],
                   padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=32), hashes.SHA256())
    except InvalidSignature:
        raise ValueError('retail NCA header signature verification failed') from None
