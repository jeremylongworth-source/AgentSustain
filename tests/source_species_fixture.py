import copy
import hashlib
from scripts.contract_validation import ROOT
from scripts.gas_mass import calculate_gas_mass
from scripts.gas_conversion import convert_gas_mass
from tests.test_gas_ledger import fixture


def matrix_fixture():
    state,old,requests=fixture(True)
    mp=copy.deepcopy(requests[0]['parameters']);mp.update(gas='CO2',result_id='raw-CO2')
    e=copy.deepcopy(next(e for e in state['evidence'] if e['id'] in mp['factor']['evidence_ids']));e.update(id='co2-factor-source',unit='g CO2/GJ')
    e['source'].update(locator='fixture:co2-factor',version='fictional-co2-1');state['evidence'].append(e)
    mp['factor'].update(id='co2-factor',gas='CO2',value=1000,unit='g CO2/GJ',evidence_ids=[e['id']])
    mp['factor']['source'].update(locator=e['source']['locator'],version=e['source']['version'])
    mp['applicability_review']['activity_review']['gas']='CO2'
    mp['applicability_review']['factor_review'].update(factor_id='co2-factor',gas='CO2',confirmed_value=1000,confirmed_unit='g CO2/GJ',evidence_ids=[e['id']],source_locator=e['source']['locator'],source_version=e['source']['version'])
    out=calculate_gas_mass(state,mp);state=out['proposal']['state']
    cp=copy.deepcopy(requests[1]['parameters']);cp.update(gas_result_id='raw-CO2',gas_metric_id=out['result']['metrics'][0]['id'],result_id='converted-CO2')
    e=copy.deepcopy(next(e for e in state['evidence'] if e['id'] in cp['gwp']['evidence_ids']));e.update(id='co2-gwp-source',unit='kg CO2e/kg CO2')
    e['source'].update(locator='fixture:co2-gwp',version='fictional-co2-1');state['evidence'].append(e)
    cp['gwp'].update(id='co2-gwp',gas='CO2',value=1,unit='kg CO2e/kg CO2',evidence_ids=[e['id']]);cp['gwp']['source'].update(locator=e['source']['locator'],version=e['source']['version'])
    cp['conversion_review'].update(gas='CO2',evidence_ids=[e['id']])
    cp['conversion_review']['source_review'].update(gwp_id='co2-gwp',gas_result_id='raw-CO2',gas_metric_id=cp['gas_metric_id'],gas='CO2',value=1,unit=cp['gwp']['unit'],evidence_ids=[e['id']],source_locator=e['source']['locator'],source_version=e['source']['version'])
    state=convert_gas_mass(state,cp)['proposal']['state']
    profile_e=copy.deepcopy(next(e for e in state['evidence'] if e['id']=='ledger-profile-source'));profile_e['id']='matrix-profile-source'
    profile_e['source'].update(locator='fixture:fictional-source-species-profile',version='fictional-matrix-1');state['evidence'].append(profile_e)
    raw=(ROOT/'standards/jurisdictions/fixtures/fictional-source-species-1.json').read_bytes()
    source=copy.deepcopy(old['sources'][0]);source.pop('gases');source['source_class']='biomass_demo'
    review=copy.deepcopy(old['ledger_review']);review.pop('exclusions');review['evidence_ids']=[profile_e['id']]
    slots=[{'source_id':source['id'],'gas':g,'status':'converted','result_id':'converted-'+g,'metric_id':None,
        'gwp':None,'gwp_review':None,'evidence_ids':['ev-001'],'evidence_fit':'reviewed_supporting','rationale':'Explicit fictional source/species conversion only.'} for g in ('CO2','CH4','N2O')]
    return state,{'profile_pin':{'path':'fixtures/fictional-source-species-1.json','sha256':hashlib.sha256(raw).hexdigest()},
        'sources':[source],'slots':slots,'coverage_review':review,'fixture_mode':True,'result_id':'species-matrix'}


def add_zero(state,p,gas='N2O'):
    source=next(r for r in state['results'] if r['metrics']);r=copy.deepcopy(source);r['id']='zero-'+gas
    e=copy.deepcopy(state['evidence'][0]);e.update(id=r['id']+'-evidence',unit='kg '+gas,period=copy.deepcopy(state['reporting_period']))
    e['source'].update(locator='fixture:direct-zero-'+gas,version='fictional-zero-1',title='Fictional supplied zero species observation, not an actual measurement.')
    state['evidence'].append(e)
    m=copy.deepcopy(source['metrics'][0]);m.update(id=r['id']+'-metric',value=0,unit='kg '+gas,period=copy.deepcopy(state['reporting_period']),evidence_ids=[e['id']])
    m['method']={'name':'Fictional supplied zero observation','version':'fictional-zero-1','source':e['source']['locator']}
    m['calculation']['inputs']=[e['id']];r.update(metrics=[m],evidence_ids=[e['id']]);state['results'].append(r)
    p['sources'][0]['evidence_ids'].append(e['id'])
    slot=next(s for s in p['slots'] if s['gas']==gas);slot.update(status='measured_zero',result_id=r['id'],metric_id=m['id'],evidence_ids=[e['id']])

    from scripts.gas_conversion import _diagnostic
    conversion=next(r for r in state['results'] if r['id']=='converted-'+gas)
    inputs=_diagnostic(conversion,'GAS_CO2E_INPUTS')
    slot['gwp']=copy.deepcopy(inputs['gwp']);slot['gwp_review']=copy.deepcopy(inputs['conversion_review']['source_review'])
    slot['gwp_review'].update(gas_result_id=r['id'],gas_metric_id=m['id'])
