import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.climate_tools import run_climate
from scripts.contract_validation import ROOT, validate_state
from tests.test_climate import report
from tests.test_climate_register import register_fixture


def priority_fixture():
    state,register=register_fixture(); state=run_climate(state,'build-climate-risk-register',register)['proposal']['state']
    note=copy.deepcopy(state['evidence'][-1]); note['id']='priority-note'; note['source'].update(title='Fictional investigation-priority rubric and ranges',locator='fixture:priority-note')
    note['method']['source']='fixture:priority-note'; note['uncertainty']['description']='Fictional conditional urgency ranges, not probabilities or verified risk ranks.'; state['evidence'].append(note)
    criteria=[]
    for ident,name in [('service-review','Potential service-consequence investigation urgency'),('evidence-review','Evidence/dependency investigation urgency')]:
        criteria.append({'id':ident,'name':name,'definition':'Supplied fictional investigation criterion applicable to selected physical and transition concerns only.',
            'levels':[{'id':'P'+str(i),'label':label,'definition':'Supplied '+label+' investigation priority; not an ordinal climate-risk class or loss.'} for i,label in [(1,'Lower'),(2,'Intermediate'),(3,'Higher')]]})
    model={'id':'selected-priority-rubric','name':'Fictional ordered interval investigation model','version':'fictional-1',
        'evidence_ids':['priority-note'],'evidence_fit':'reviewed_supporting','criteria':criteria,'priority_order':['service-review','evidence-review']}
    ranges={'entry-0':[('P3','P3'),('P1','P1')],'entry-1':[('P2','P3'),('P3','P3')],
        'entry-2':[('P1','P1'),('P1','P1')],'entry-3':[('P1','P1'),('P2','P2')],'entry-4':[('P2','P2')]}
    ratings=[]
    for entry,values in ranges.items():
        for criterion,(lower,upper) in zip(model['priority_order'],values):
            ratings.append({'entry_id':entry,'criterion_id':criterion,'lower_level_id':lower,'upper_level_id':upper,
                'evidence_ids':['priority-note'],'evidence_fit':'reviewed_supporting','observed_date':'2026-10-03',
                'rationale':'Fictional explicitly sourced investigation bounds, not normalized source risk scores.',
                'source_fragment':'Fictional supplied '+entry+' / '+criterion+' range '+lower+' through '+upper+'.',
                'limitations':'Qualified service/source/model and owner review unresolved; not implementation priority.'})
    review=copy.deepcopy(register['register_review']); review.update(method='sourced_climate_priority',evidence_ids=['priority-note'],
        model_fit_rationale='Supplied investigation criteria and ordered intervals apply jointly to selected concerns; no comparison of underlying climate matrices/scenarios.')
    rec=report({'result':state['results'][-1]},'CLIMATE_RISK_REGISTER')
    review['entry_contexts']={e['id']:{'evidence_ids':sorted(set(e['source_evidence_ids']+e['evidence_ids'])),'evidence_fit':'reviewed_supporting',
        'rationale':'Selected source contexts retained for investigation urgency, not risk authentication or owner acceptance.'} for e in rec['entries']}
    return state,{'register_result_id':register['result_id'],'model':model,'ratings':ratings,'priority_review':review,'result_id':'climate-priorities'}


class ClimatePriorityTests(unittest.TestCase):
    def test_interval_fronts_overlap_and_missing_rating_without_default_order(self):
        state,p=priority_fixture(); original=copy.deepcopy(state); out=run_climate(state,'prioritize-climate-risks',p); rec=report(out,'CLIMATE_RISK_PRIORITIES')
        self.assertEqual(out['result']['status'],'partial'); self.assertEqual(rec['definite_precedence_fronts'],[['entry-0','entry-1'],['entry-3'],['entry-2']])
        self.assertEqual(rec['unassessed_entry_ids'],['entry-4']); self.assertTrue(rec['fronts_are_not_ties_or_complete_order'])
        pair=next(x for x in rec['pairwise_comparisons'] if x['left_entry_id']=='entry-0' and x['right_entry_id']=='entry-1')
        self.assertEqual(pair['relation'],'unresolved_overlap'); self.assertEqual(pair['decisive_criterion_id'],'service-review')
        self.assertFalse(rec['priority_approved']); self.assertIsNone(rec['risk_rank']); self.assertEqual(out['result']['metrics'],[])
        self.assertEqual(state,original); final=out['proposal']['state']; self.assertEqual(final['results'][:-1],state['results'])
        for k,v in state.items():
            if k in ['assumptions','data_gaps','review_requirements']:
                for x in v: self.assertIn(x,final[k])
            elif k not in ['revision','results']: self.assertEqual(v,final[k])
        validate_state(final)

    def test_exact_tie_is_retained_without_id_tie_breaker(self):
        state,p=priority_fixture(); r=next(x for x in p['ratings'] if x['entry_id']=='entry-3' and x['criterion_id']=='evidence-review'); r.update(lower_level_id='P1',upper_level_id='P1')
        rec=report(run_climate(state,'prioritize-climate-risks',p),'CLIMATE_RISK_PRIORITIES')
        pair=next(x for x in rec['pairwise_comparisons'] if x['left_entry_id']=='entry-2' and x['right_entry_id']=='entry-3')
        self.assertEqual(pair['relation'],'exact_tie'); self.assertEqual(rec['definite_precedence_fronts'][-1],['entry-2','entry-3'])

    def test_unknown_unfit_bounds_and_context_leave_concern_unassessed(self):
        for mode in ['lower','upper','fit','context','date']:
            state,p=priority_fixture(); r=p['ratings'][0]
            if mode=='lower': r['lower_level_id']=None
            if mode=='upper': r['upper_level_id']=None
            if mode=='fit': r['evidence_fit']='irrelevant'
            if mode=='context': p['priority_review']['entry_contexts']['entry-0']['evidence_fit']='unverified'
            if mode=='date': r['observed_date']=None
            rec=report(run_climate(state,'prioritize-climate-risks',p),'CLIMATE_RISK_PRIORITIES')
            self.assertIn('entry-0',rec['unassessed_entry_ids']); self.assertNotIn('entry-0',sum(rec['definite_precedence_fronts'],[]))
            physical=rec['entries'][0]['entry_snapshot']['characterization']; self.assertEqual(physical['possible_risk_level_ids'],['R2','R3']); self.assertFalse(physical['safe'])

    def test_invalid_model_bounds_references_source_dates_and_context_block(self):
        for mode in ['order','model-fit','duplicate-level','bounds','level','entry','duplicate','future','contexts','sources','scope']:
            state,p=priority_fixture()
            if mode=='order': p['model']['priority_order']=['service-review','service-review']
            if mode=='model-fit': p['model']['evidence_fit']='unverified'
            if mode=='duplicate-level': p['model']['criteria'][0]['levels'].append(copy.deepcopy(p['model']['criteria'][0]['levels'][0]))
            if mode=='bounds': p['ratings'][0].update(lower_level_id='P3',upper_level_id='P1')
            if mode=='level': p['ratings'][0]['lower_level_id']='R3'
            if mode=='entry': p['ratings'][0]['entry_id']='missing'
            if mode=='duplicate': p['ratings'].append(copy.deepcopy(p['ratings'][0]))
            if mode=='future': p['ratings'][0]['observed_date']='2026-10-06'
            if mode=='contexts': p['priority_review']['entry_contexts'].pop('entry-0')
            if mode=='sources': p['priority_review']['entry_contexts']['entry-0']['evidence_ids']=['priority-note']
            if mode=='scope': p['priority_review']['scope']='Different organization'
            self.assertEqual(run_climate(state,'prioritize-climate-risks',p)['result']['status'],'blocked',mode)

    def test_all_missing_ratings_not_a_clearance_or_ranked_last(self):
        state,p=priority_fixture(); p['ratings']=[]; p['priority_review'].update(coverage_complete=True,exclusions=[])
        out=run_climate(state,'prioritize-climate-risks',p); rec=report(out,'CLIMATE_RISK_PRIORITIES')
        self.assertEqual(out['result']['status'],'partial'); self.assertEqual(rec['definite_precedence_fronts'],[]); self.assertEqual(len(rec['unassessed_entry_ids']),5)

    def test_parent_lineage_and_missing_factor_block(self):
        for mode in ['lineage','factor']:
            state,p=priority_fixture(); parent=next(r for r in state['results'] if r['id']=='climate-register')
            if mode=='lineage': parent['evidence_ids']=['priority-note']
            else: parent['diagnostics'].append({'code':'EMISSION_FACTOR_REQUIRED','message':'Unresolved selected source factor.'})
            out=run_climate(state,'prioritize-climate-risks',p); self.assertEqual(out['result']['status'],'blocked')
            if mode=='factor': self.assertTrue(any(d['code']=='EMISSION_FACTOR_REQUIRED' for d in out['result']['diagnostics']))

    def test_cli_complete_output_and_request_integrity(self):
        state,p=priority_fixture(); req={'contract_version':'0.1.0','skill':'prioritize-climate-risks','state':state,'parameters':p}
        with tempfile.TemporaryDirectory() as temp:
            f=Path(temp)/'request.json'; f.write_text(json.dumps(req),encoding='utf-8'); before=f.read_bytes()
            run=subprocess.run([sys.executable,'-m','scripts.run_climate',str(f)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stderr); self.assertEqual(json.loads(run.stdout),run_climate(state,req['skill'],p)); self.assertEqual(f.read_bytes(),before)


if __name__=='__main__': unittest.main()
