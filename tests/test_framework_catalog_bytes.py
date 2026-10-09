import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts.contract_validation import ROOT
from scripts.framework_tools import run_framework


class FrameworkCatalogBytesTests(unittest.TestCase):
    def test_catalog_pins_survive_git_checkouts_with_both_autocrlf_settings(self):
        if not shutil.which('git'):
            self.skipTest('Git is required for checkout portability verification')
        source = ROOT / 'standards/frameworks'
        with tempfile.TemporaryDirectory(prefix='agentsustain-catalog-checkout-') as directory:
            repo = Path(directory) / 'source'
            repo.mkdir()
            def git(*args, cwd=repo):
                return subprocess.check_output(['git', *args], cwd=cwd, stderr=subprocess.PIPE)
            git('init')
            target = repo / 'standards/frameworks'
            target.mkdir(parents=True)
            shutil.copyfile(source / '.gitattributes', target / '.gitattributes')
            catalogs = list(source.glob('*.json'))
            for catalog in catalogs:
                shutil.copyfile(catalog, target / catalog.name)
                self.assertNotIn(b'\r', catalog.read_bytes())
            git('-c', 'core.autocrlf=true', 'add', '.')
            git('-c', 'user.name=Fixture Reviewer', '-c', 'user.email=fixture@example.invalid',
                'commit', '-m', 'Fictional catalog checkout test')
            for setting in ('true', 'false'):
                with self.subTest(autocrlf=setting):
                    checkout = Path(directory) / setting
                    git('-c', 'core.autocrlf=' + setting, 'clone', '--no-local', str(repo), str(checkout))
                    for catalog in catalogs:
                        relative = 'standards/frameworks/' + catalog.name
                        expected = catalog.read_bytes()
                        self.assertEqual(git('show', 'HEAD:' + relative), expected)
                        self.assertEqual((checkout / relative).read_bytes(), expected)

    def test_canonical_capture_replays_and_preserves_original_source_state(self):
        capture = json.loads((ROOT / 'evaluations/sus25-fictional-framework-replay.json').read_text())
        for execution in capture['executions']:
            request = execution['request']
            self.assertEqual(run_framework(request['state'], request['skill'], request['parameters']),
                             execution['output'])
        self.assertFalse(capture['independent_acceptance'])
        for execution in capture['executions']:
            original=execution['request']['state']
            final=execution['output']['proposal']['state']
            self.assertEqual(final['results'][:len(original['results'])],original['results'])
        for migration in capture['catalog_pin_migration']:
            path = ROOT / migration['path']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), migration['canonical_lf_sha256'])

    def test_historical_crlf_pin_is_rejected_instead_of_silently_normalized(self):
        from tests.test_frameworks import framework_fixture
        state,parameters=framework_fixture()
        selected=parameters['adapters'][0]
        raw=(ROOT/'standards/frameworks'/(selected['adapter_id']+'.json')).read_bytes()
        selected['catalog_sha256']=hashlib.sha256(raw.replace(b'\n',b'\r\n')).hexdigest()
        request={'state':state,'skill':'map-framework-disclosures','parameters':parameters}
        output = run_framework(request['state'], request['skill'], request['parameters'])
        self.assertEqual(output['result']['status'], 'blocked')
