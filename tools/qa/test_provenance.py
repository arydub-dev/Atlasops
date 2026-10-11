import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('provenance',Path(__file__).with_name('provenance.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ProvenanceTests(unittest.TestCase):
    def test_runtime_secrets_and_generated_files_excluded(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for name in ['backend/app/main.py','backend/app/.env','backend/app/__pycache__/cache.py','frontend/app/page.tsx','.local/private.json']:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic')
            result=module.snapshot(root)
            self.assertEqual(set(result['files']),{'backend/app/main.py','frontend/app/page.tsx'})
            self.assertIsNone(result['git']['revision'])
    def test_content_change_changes_identity(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'backend/app/main.py';p.parent.mkdir(parents=True);p.write_text('before')
            first=module.snapshot(root);self.assertEqual(first,module.snapshot(root))
            p.write_text('after');self.assertNotEqual(first['source_sha256'],module.snapshot(root)['source_sha256'])
