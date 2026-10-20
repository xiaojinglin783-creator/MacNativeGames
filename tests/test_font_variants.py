"""Synthetic font bytes exercise accepted variants and runtime-manifest binding."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import build_app


class FontVariantTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.names = tuple(build_app.EXPECTED['shared_fonts_sha256'])
        self.expected = {}
        for i, name in enumerate(self.names):
            data = b'synthetic original font ' + bytes([i])
            (self.folder / f'{i}-{name}.bfttf').write_bytes(data)
            self.expected[name] = hashlib.sha256(data).hexdigest()
        self.expected_patch = patch.dict(build_app.EXPECTED, {'shared_fonts_sha256': self.expected})
        self.expected_patch.start()
        self.addCleanup(self.expected_patch.stop)

    def variant(self):
        data = b'synthetic independently verified firmware font'
        (self.folder / '1-chinese-simplified.bfttf').write_bytes(data)
        return {'chinese-simplified': (hashlib.sha256(data).hexdigest(), len(data))}

    def test_original_fonts_remain_supported(self):
        report = build_app.font_report(self.folder)
        self.assertEqual([r['sha256'] for r in report['fonts']], list(self.expected.values()))

    def test_variant_actual_hash_and_size_bind_runtime_manifest(self):
        variants = self.variant()
        with patch.object(build_app, 'VERIFIED_FONT_VARIANTS', variants):
            report = build_app.font_report(self.folder)
            row = report['fonts'][1]
            self.assertEqual((row['sha256'], row['bfttf_bytes']), variants['chinese-simplified'])
            self.assertEqual(row['font_bytes'], row['bfttf_bytes'] - 8)
            (self.folder / 'manifest.json').write_text(json.dumps(report))
            build_app.validate_fonts(self.folder)
            report['fonts'][1]['sha256'] = self.expected['chinese-simplified']
            (self.folder / 'manifest.json').write_text(json.dumps(report))
            with self.assertRaisesRegex(build_app.BuildError, 'manifest differs'):
                build_app.validate_fonts(self.folder)

    def test_unreviewed_or_modified_font_is_rejected(self):
        self.variant()
        with self.assertRaisesRegex(build_app.BuildError, 'shared font chinese-simplified'):
            build_app.font_report(self.folder)

    def test_variant_is_bound_to_type_and_size(self):
        variants = self.variant()
        digest, size = variants['chinese-simplified']
        for value in ({'standard': (digest, size)}, {'chinese-simplified': (digest, size+1)}):
            with patch.object(build_app, 'VERIFIED_FONT_VARIANTS', value), self.assertRaises(build_app.BuildError):
                build_app.font_report(self.folder)
