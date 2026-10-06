import copy
import hashlib
from scripts.contract_validation import ROOT
from tests.source_species_fixture import matrix_fixture,add_zero


def direct_fixture(gas='N2O',mass=0.004):
    state,p=matrix_fixture();raw=(ROOT/'standards/jurisdictions/fixtures/fictional-source-species-2.json').read_bytes()
    p['profile_pin']={'path':'fixtures/fictional-source-species-2.json','sha256':hashlib.sha256(raw).hexdigest()}
    e=next(e for e in state['evidence'] if e['id']=='matrix-profile-source')
    e['source'].update(locator='fixture:fictional-source-species-profile-2',version='fictional-matrix-2')
    add_zero(state,p,gas);slot=next(s for s in p['slots'] if s['gas']==gas)
    owner=next(r for r in state['results'] if r['id']==slot['result_id']);m=owner['metrics'][0]
    e=next(e for e in state['evidence'] if e['id']==m['evidence_ids'][0])
    old_e=e['id'];e['id']='measured-'+gas+'-evidence';e['source'].update(locator='fixture:direct-mass-'+gas,title='Fictional supplied species measurement; no actual metrology.')
    e['assumption']='Fictional supplied species measurement only.'
    owner.update(id='measured-'+gas,evidence_ids=[e['id']])
    m.update(id=owner['id']+'-metric',name='Fictional supplied '+gas+' mass',value=mass,evidence_ids=[e['id']],assumption=e['assumption'])
    m['method'].update(name='Fictional direct species observation',source=e['source']['locator']);m['calculation']['inputs']=[e['id']]
    owner['assumptions']=[e['assumption']]
    if e['assumption'] not in state['assumptions']:state['assumptions'].append(e['assumption'])
    p['sources'][0]['evidence_ids']=[e['id'] if ident==old_e else ident for ident in p['sources'][0]['evidence_ids']]
    slot.update(status='measured_mass',result_id=owner['id'],metric_id=m['id'],evidence_ids=[e['id']])
    slot['gwp_review'].update(gas_result_id=owner['id'],gas_metric_id=m['id'])
    return state,p
