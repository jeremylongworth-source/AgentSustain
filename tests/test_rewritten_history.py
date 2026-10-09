"""Verify integrity closure in the clean protocol clone, without old Git objects."""
import json
import subprocess
import unittest

from scripts.contract_validation import ROOT
from scripts.intent_router import APPROVED_REVISION
from scripts.specialist_router import REVISION, load_specialist_catalog
from tests.test_specialist_router import router_fixture


class RewrittenHistoryTests(unittest.TestCase):
    def test_runtime_pins_resolve_to_transformed_reviewed_commits(self):
        migration=json.loads((ROOT/'evaluations/sus25-rewritten-capability-migration.json').read_bytes())
        self.assertEqual(APPROVED_REVISION,migration['transformed_intent_revision'])
        self.assertEqual(REVISION,migration['transformed_source_revision'])
        for revision in (APPROVED_REVISION,REVISION):
            actual=subprocess.check_output(['git','cat-file','-t',revision],cwd=ROOT).decode().strip()
            self.assertEqual(actual,'commit')
        _,parameters=router_fixture()
        _,available=load_specialist_catalog(parameters['catalog_pin'])
        self.assertTrue(all(available.values()))
        self.assertFalse(migration['integrity_checks_bypassed'])

    def test_original_source_payload_objects_are_absent_from_clean_clone(self):
        manifest=json.loads((ROOT/'evaluations/sus25-source-remediation-history-manifest.json').read_bytes())
        ids=sorted({v['git_blob'] for v in manifest['occurrences']})
        out=subprocess.check_output(['git','cat-file','--batch-check'],cwd=ROOT,input=('\n'.join(ids)+'\n').encode()).decode().splitlines()
        self.assertEqual(len(out),len(ids))
        self.assertTrue(all(line.endswith(' missing') for line in out),
                        'Old source-dependent objects remain; verify a fresh protocol clone instead of the private rewriting workspace.')

    def test_commit_identities_and_public_refs_do_not_reintroduce_original_metadata(self):
        emails=set(subprocess.check_output(['git','log','--all','--format=%ae%n%ce'],cwd=ROOT,text=True).splitlines())
        self.assertEqual(emails,{'264607751+jeremylongworth-source@users.noreply.github.com'})
        refs=subprocess.check_output(['git','for-each-ref','--format=%(refname)'],cwd=ROOT,text=True).splitlines()
        self.assertFalse(any(ref.startswith('refs/codex/') for ref in refs))
        self.assertFalse(any('backup' in ref for ref in refs))
