import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts.framework_tools import catalog, run_framework
from scripts.jurisdiction_tools import read_pinned_pack
from scripts.canada_ghgrp import screen_canada_ghgrp
from tests.test_frameworks import framework_fixture, pin
from scripts.contract_validation import ROOT


class SourcePackAvailabilityTests(unittest.TestCase):
    def test_omitted_real_catalog_blocks_without_losing_prior_state_or_reviews(self):
        state,p=framework_fixture();original=copy.deepcopy(state)
        p['adapters'][0].update(adapter_id='ghgp-corporate-2004',catalog_sha256='0'*64)
        out=run_framework(state,'map-framework-disclosures',p)
        self.assertEqual(out['result']['status'],'blocked')
        self.assertIn('SOURCE_PACK_REQUIRED',[d['code'] for d in out['result']['diagnostics']])
        self.assertEqual(out['result']['metrics'],[])
        self.assertEqual(state,original)
        self.assertEqual(out['proposal']['state']['results'][:-1],state['results'])
        for review in state['review_requirements']:self.assertIn(review,out['result']['review_requirements'])

    def test_missing_pack_cli_reports_refusal_and_preserves_request_bytes(self):
        state,_=framework_fixture()
        request={'contract_version':'0.1.0','skill':'screen-subject-jurisdiction-applicability','state':state,
                 'parameters':{'pack_pins':[{'path':'canada/ghgrp/notice-2023.json','sha256':'0'*64}],'fixture_mode':True}}
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'request.json';raw=json.dumps(request).encode();path.write_bytes(raw)
            out=subprocess.run([sys.executable,'-m','scripts.run_canada_ghgrp',str(path)],cwd=ROOT,capture_output=True)
            self.assertEqual(out.returncode,2)
            self.assertEqual(json.loads(out.stdout)['error'],'SOURCE_PACK_REQUIRED')
            self.assertEqual(path.read_bytes(),raw)

    def test_fictional_catalog_requires_fixture_mode_and_cannot_claim_issued_source(self):
        selected=pin('fictional-review-exercise-2')
        with self.assertRaises(ValueError):catalog(selected['adapter_id'],selected['catalog_sha256'])
        value=catalog(selected['adapter_id'],selected['catalog_sha256'],True)
        self.assertTrue(value['synthetic']);self.assertFalse(value['source_verified'])
        self.assertEqual(value['publication_status'],'fictional')
        with patch('scripts.framework_tools.json.loads',return_value=dict(value,publication_status='issued')):
            with self.assertRaises(ValueError):catalog(selected['adapter_id'],selected['catalog_sha256'],True)

    def test_fictional_version_diff_needs_explicit_fixture_mode(self):
        state,p=framework_fixture()
        args={'before':pin('fictional-review-exercise-1'),'after':pin('fictional-review-exercise-2'),
              'mapping_review':p['mapping_review'],'result_id':'fictional-diff'}
        self.assertEqual(run_framework(state,'compare-framework-mappings',args)['result']['status'],'blocked')
        args['fixture_mode']=True
        out=run_framework(state,'compare-framework-mappings',args)
        self.assertEqual(out['result']['status'],'partial')
        self.assertIn('PROFESSIONAL_REVIEW_REQUIRED',out['result']['review_states'])

    def test_missing_canadian_pack_is_explicit_and_does_not_fall_back_to_fictional_rules(self):
        pin={'path':'canada/ghgrp/notice-2023.json','sha256':'0'*64}
        with self.assertRaisesRegex(ValueError,'SOURCE_PACK_REQUIRED'):read_pinned_pack(pin)
        state,_=framework_fixture();original=copy.deepcopy(state)
        with self.assertRaisesRegex(ValueError,'SOURCE_PACK_REQUIRED'):
            screen_canada_ghgrp(state,{'pack_pins':[pin],'fixture_mode':True})
        self.assertEqual(state,original)
