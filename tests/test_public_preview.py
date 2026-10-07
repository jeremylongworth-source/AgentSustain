import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile

from scripts.prepare_public_preview import ROOT, prepare, source_closure


class PublicPreviewTests(unittest.TestCase):
    def test_package_dependencies_exclusions_links_and_actual_execution(self):
        base = ROOT / 'private-data/public-preview'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temporary:
            self.assertTrue(Path(temporary).resolve().is_relative_to(base.resolve()))
            output = Path(temporary) / 'prepared'
            receipt = prepare(output)
            archive = ROOT / receipt['archive']
            self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), receipt['sha256'])
            tree = output / 'tree'
            with zipfile.ZipFile(archive) as package:
                names = package.namelist()
                self.assertEqual(len(names), len(set(names)))
                self.assertTrue(all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in names))
                self.assertFalse(any(n.startswith(('standards/', 'evaluations/', 'private-data/', '.git/', '.github/', 'data/', 'skills/', 'skillsets/', 'router/')) for n in names))
                for name in names:
                    self.assertEqual(package.read(name), (tree / name).read_bytes())
            manifest = json.loads((tree / 'PREVIEW-MANIFEST.json').read_text())
            self.assertFalse(manifest['publication_authorized'])
            self.assertFalse(manifest['license_selected'])
            self.assertFalse(manifest['public_v1_readiness'])
            for name, pin in manifest['files'].items():
                self.assertEqual(hashlib.sha256((tree / name).read_bytes()).hexdigest(), pin['sha256'])
            for markdown in tree.rglob('*.md'):
                for link in re.findall(r'\]\(([^)]+)\)', markdown.read_text()):
                    if '://' not in link and not link.startswith('#'):
                        self.assertTrue((markdown.parent / link.split('#')[0]).is_file(), (markdown, link))
            # Execute only the packaged source. This catches omitted relative
            # imports and schemas that source-checkout execution can conceal.
            imported = subprocess.run([sys.executable, '-c',
                'import scripts.run_energy, scripts.run_water, scripts.run_resources, scripts.run_finance'],
                cwd=tree, capture_output=True, text=True)
            self.assertEqual(imported.returncode, 0, imported.stderr)
            request = tree / 'examples/preview-conversion.json'
            original = request.read_bytes()
            actual = subprocess.run([sys.executable, '-m', 'scripts.data_tools', str(request)],
                                    cwd=tree, capture_output=True, text=True)
            self.assertEqual(actual.returncode, 0, actual.stderr)
            self.assertEqual(json.loads(actual.stdout)['value'], 2000)
            self.assertEqual(request.read_bytes(), original)
            invalid = tree / 'invalid.json'
            invalid.write_text(json.dumps({'operation':'convert','value':1,'source_unit':'CAD','target_unit':'kWh'}))
            refused = subprocess.run([sys.executable, '-m', 'scripts.data_tools', str(invalid)],
                                     cwd=tree, capture_output=True, text=True)
            self.assertEqual(refused.returncode, 2)
            self.assertEqual(json.loads(refused.stdout)['error'], 'INVALID_INPUT')

    def test_fresh_output_and_private_boundary_required(self):
        with self.assertRaises(ValueError):
            prepare(ROOT / 'public-preview')
        base = ROOT / 'private-data/public-preview'
        base.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as temporary:
            self.assertTrue(Path(temporary).resolve().is_relative_to(base.resolve()))
            marker = Path(temporary) / 'keep.txt'
            marker.write_text('existing user material')
            with self.assertRaises(ValueError):
                prepare(Path(temporary))
            self.assertEqual(marker.read_text(), 'existing user material')

    def test_relative_import_closure_is_original_source_only(self):
        names = source_closure()
        self.assertTrue(names)
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(n.startswith('scripts/') and n.endswith('.py') for n in names))
        self.assertNotIn('scripts/prepare_public_preview.py', names)
