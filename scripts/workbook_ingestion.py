"""Bounded literal SpreadsheetML ingestion; no Excel/formula execution or unit guessing."""
import copy
from datetime import date
import hashlib
import io
import json
import re
from urllib.parse import quote
import zipfile
import zlib
from xml.etree import ElementTree as ET
from jsonschema import ValidationError
from .business_ingestion import HEADERS, _quantity
from .climate_tools import _fields
from .contract_validation import ROOT,validate_state,validate_shape
from .manager_workflow import _empty
from .state_proposal import propose

S='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R='{http://schemas.openxmlformats.org/package/2006/relationships}'
RID='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
CONTRACT='business-xlsx-ingestion-0.1.0'


def _xml(raw):
    text=raw.decode('utf-8-sig')
    if '\x00' in text or '<!DOCTYPE' in text or '<!ENTITY' in text:
        raise ValueError('UTF-8 XML without DTD/entity declarations required.')
    return ET.fromstring(text)


def _target(base,target):
    if not isinstance(target,str) or not target or ':' in target or '\\' in target or any(p in {'..','.'} for p in target.split('/')):
        raise ValueError('Bounded internal package relationship target required.')
    return target[1:] if target.startswith('/') else base+target


def _text(element):
    if element is None:return ''
    if any(n.tag==S+'rPh' for n in element.iter()):raise ValueError('Phonetic/ambiguous string annotations unsupported.')
    return ''.join(n.text or '' for n in element.iter(S+'t'))


def read_literal_workbook(raw,sheet_name):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos=archive.infolist();names=[i.filename for i in infos]
        if len(infos)>64 or len(names)!=len(set(names)) or sum(i.file_size for i in infos)>8388608:
            raise ValueError('Bounded distinct workbook package parts required.')
        parts={}
        for info in infos:
            name=info.filename;lower=name.lower()
            if (info.is_dir() or name.startswith('/') or ':' in name or '\\' in name or any(p in {'..','.'} for p in name.split('/'))
                or info.flag_bits&1 or info.compress_type not in {zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED}
                or info.file_size>2097152 or info.file_size>max(info.compress_size,1)*200):
                raise ValueError('Safe bounded unencrypted internal ZIP members required.')
            if any(token in lower for token in ('vbaproject','externallink','connections','querytable','embedding','activex')):
                raise ValueError('Macro, external-data, query or embedded active content unsupported.')
            parts[name]=archive.read(info)
        if not {'[Content_Types].xml','_rels/.rels','xl/workbook.xml','xl/_rels/workbook.xml.rels'}<=set(parts):
            raise ValueError('Complete supported workbook package required.')
        for name,data in parts.items():
            if name.endswith(('.xml','.rels')):
                root=_xml(data)
                if name.endswith('.rels'):
                    if root.tag!=R+'Relationships' or any(n.tag!=R+'Relationship' for n in root):raise ValueError('Supported relationship namespace required.')
                    for rel in root:
                        if rel.get('TargetMode','Internal')!='Internal':raise ValueError('External relationships are not followed or imported.')
                        _target('',rel.get('Target'))
                if name=='[Content_Types].xml' and any('macro' in (n.get('ContentType') or '').lower() for n in root):
                    raise ValueError('Macro-enabled workbook content unsupported.')
        content=_xml(parts['[Content_Types].xml']);types='{http://schemas.openxmlformats.org/package/2006/content-types}'
        overrides=[n for n in content if n.tag==types+'Override' and n.get('PartName')=='/xl/workbook.xml']
        defaults=[n for n in content if n.tag==types+'Default' and n.get('Extension')=='xml']
        selected_type=overrides if overrides else defaults
        if content.tag!=types+'Types' or len(overrides)>1 or len(defaults)>1 or len(selected_type)!=1 or selected_type[0].get('ContentType')!='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml':
            raise ValueError('Explicit standard XLSX workbook content type required.')
        roots=_xml(parts['_rels/.rels'])
        docs=[r for r in roots if r.get('Type')==REL+'officeDocument']
        if len(docs)!=1 or _target('',docs[0].get('Target'))!='xl/workbook.xml':raise ValueError('Exact supported workbook root required.')
        workbook=_xml(parts['xl/workbook.xml']);sheets=workbook.findall(S+'sheets/'+S+'sheet')
        if workbook.tag!=S+'workbook' or not sheets or len({s.get('name','').casefold() for s in sheets})!=len(sheets):
            raise ValueError('Distinct supported named worksheets required.')
        selected=[s for s in sheets if s.get('name')==sheet_name]
        if len(selected)!=1 or selected[0].get('state','visible')!='visible':raise ValueError('Exactly one explicit visible selected worksheet required.')
        relationships=_xml(parts['xl/_rels/workbook.xml.rels']);mapping={}
        for rel in relationships:
            ident=rel.get('Id')
            if not ident or ident in mapping:raise ValueError('Distinct workbook relationship identities required.')
            mapping[ident]=rel
        relation=mapping.get(selected[0].get(RID))
        if relation is None or relation.get('Type')!=REL+'worksheet':raise ValueError('Selected sheet must resolve to a worksheet part.')
        worksheet_part=_target('xl/',relation.get('Target'))
        if worksheet_part not in parts:raise ValueError('Complete selected worksheet part required.')
        shared=[];strings=[r for r in relationships if r.get('Type')==REL+'sharedStrings']
        if len(strings)>1:raise ValueError('Unambiguous shared-string table required.')
        if strings:
            string_part=_target('xl/',strings[0].get('Target'))
            if string_part not in parts:raise ValueError('Shared strings must resolve inside this package.')
            root=_xml(parts[string_part])
            if root.tag!=S+'sst':raise ValueError('Supported shared-string root required.')
            shared=[_text(si) for si in root.findall(S+'si')]
        sheet=_xml(parts[worksheet_part])
        if sheet.tag!=S+'worksheet':raise ValueError('Supported selected worksheet namespace required.')
        if any(sheet.find(S+name) is not None for name in ('mergeCells','drawing','legacyDrawing','extLst','tableParts','dataValidations')):
            raise ValueError('Selected source must be a literal unmerged table without ambiguous objects/features.')
        if any(n.get('hidden') not in {None,'0','false'} for n in sheet.findall(S+'cols/'+S+'col')):
            raise ValueError('Hidden selected source columns unsupported.')
        grid=[];snapshots=[];rows=sheet.findall(S+'sheetData/'+S+'row')
        if not 2<=len(rows)<=201:raise ValueError('Header and 1-200 explicit source rows required.')
        for expected,row in enumerate(rows,1):
            if row.get('r')!=str(expected) or row.get('hidden') not in {None,'0','false'} or row.get('ht')=='0':
                raise ValueError('Contiguous visible source row identities required.')
            values=['']*len(HEADERS);cells={}
            for cell in row.findall(S+'c'):
                address=cell.get('r','');match=re.fullmatch(r'([A-Q])([1-9][0-9]*)',address)
                if not match or int(match[2])!=expected or address in cells:raise ValueError('Distinct bounded cell references matching their row required.')
                if any(n.tag==S+'f' for n in cell.iter()):raise ValueError('Formulas and cached formula results are never imported or evaluated.')
                if set(cell.attrib)-{'r','s','t'} or any(n.tag not in {S+'v',S+'is'} for n in cell) or len(cell.findall(S+'v'))>1 or len(cell.findall(S+'is'))>1:
                    raise ValueError('Unambiguous literal cell attributes/content required.')
                column=ord(match[1])-65;kind=cell.get('t','n');literal=cell.findtext(S+'v',default='')
                if (kind=='inlineStr' and cell.find(S+'v') is not None) or (kind!='inlineStr' and cell.find(S+'is') is not None):
                    raise ValueError('Cell type and literal representation must agree.')
                if kind=='s':
                    if not literal.isdigit() or int(literal)>=len(shared):raise ValueError('Valid shared-string index required.')
                    value=shared[int(literal)]
                elif kind=='inlineStr':value=_text(cell.find(S+'is'))
                elif kind=='str':value=literal
                elif kind=='n':
                    if expected==1 or column not in {4,14}:raise ValueError('Identifiers, ISO periods and context are explicit text; numeric date/label inference unsupported.')
                    value=literal
                else:raise ValueError('Boolean/error/date cell types unsupported.')
                values[column]=value;cells[address]={'cell':address,'ooxml_type':kind,'literal_v':literal,'value_text':value,'style_index':cell.get('s')}
            grid.append(values);snapshots.append({'worksheet_row':expected,'cells':list(cells.values())})
        if grid[0]!=HEADERS:raise ValueError('Exact distinct business-record headers in A1:Q1 required.')
        return [dict(zip(HEADERS,r)) for r in grid[1:]],snapshots[1:],{'worksheet_part':worksheet_part,'sheet_names':[s.get('name') for s in sheets],
            'selected_scope':'Complete explicit selected worksheet only','part_sha256':{n:hashlib.sha256(v).hexdigest() for n,v in parts.items()}}


def ingest_business_xlsx(state,p):
    validate_state(state);_fields(p,{'file_pin','source_metadata','sheet_name','fixture_mode','result_id','document_evidence_id'},('sheet_name','result_id','document_evidence_id'))
    if type(p['fixture_mode']) is not bool or any(r['id']==p['result_id'] for r in state['results']):raise ValueError('Explicit fixture mode and fresh result identity required.')
    result=_empty(state,'normalize-sustainability-data',p['result_id']);result['status']='partial';additions=[]
    try:
        pin=p['file_pin'];meta=p['source_metadata'];_fields(pin,{'path','sha256','source_version','synthetic'},('path','sha256','source_version'))
        _fields(meta,{'title','publisher','accessed','tier'},('title','publisher','accessed'))
        path=ROOT/pin['path'];base=ROOT/'data/inputs'
        if (type(pin['synthetic']) is not bool or not pin['path'].startswith('data/inputs/') or '\\' in pin['path'] or '..' in path.parts
            or not path.resolve().is_relative_to(base.resolve()) or path.suffix.lower()!='.xlsx' or not path.is_file() or path.stat().st_size>1048576):
            raise ValueError('Explicit versioned bounded workspace XLSX input required.')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=pin['sha256']:raise ValueError('Workbook bytes differ from selected pin.')
        if pin['synthetic'] and not p['fixture_mode']:raise ValueError('Synthetic workbook requires explicit fixture mode.')
        shipped=base/'fictional-business-records.xlsx'
        if not pin['synthetic']:
            if shipped.exists() and (not shipped.resolve().is_relative_to(base.resolve()) or shipped.stat().st_size>1048576):raise ValueError('Bounded recognized fixture lookup required.')
            if pin['path']=='data/inputs/fictional-business-records.xlsx' or shipped.exists() and raw==shipped.read_bytes():raise ValueError('Recognized fictional workbook cannot be relabeled ordinary data.')
        rows,locations,package=read_literal_workbook(raw,p['sheet_name'])
        known={e['id'] for e in state['evidence']}|{m['id'] for r in state['results'] for m in r['metrics']};document_id=p['document_evidence_id']
        if document_id in known:raise ValueError('Fresh workbook document evidence identity required.')
        known.add(document_id);record_ids=set();metrics=[];evidence=[];snapshots=[]
        locator='workspace:'+pin['path'];method={'name':'Pinned literal SpreadsheetML ingestion without formulas or unit conversion','version':CONTRACT,'source':locator}
        source={**copy.deepcopy(meta),'locator':locator,'version':pin['source_version']}
        quality={'reliability':'unknown','completeness':'unknown','fitness_notes':'Pinned selected sheet/cell identity; source authenticity, sampling and organization completeness unverified.'}
        for index,(row,location) in enumerate(zip(rows,locations),2):
            if any(not row[k].strip() for k in ('record_id','evidence_id','metric_id','name','unit','boundary_id','geography','uncertainty_description')):
                raise ValueError('Explicit identities, units, boundary, geography and uncertainty description required.')
            if row['record_id'] in record_ids or row['evidence_id'] in known or row['metric_id'] in known or row['metric_id']==row['evidence_id']:
                raise ValueError('Distinct fresh record/evidence/metric identities required.')
            record_ids.add(row['record_id']);known.update((row['evidence_id'],row['metric_id']))
            if row['boundary_id']!=state['organizational_boundary']['id'] or row['kind'] not in {'measurement','model_input','assumption','unknown'}:
                raise ValueError('Explicit matched boundary and supported attributed record kind required.')
            start=date.fromisoformat(row['period_start']);end=date.fromisoformat(row['period_end'])
            if start>end:raise ValueError('Source period is reversed.')
            period={'start':row['period_start'],'end':row['period_end']};value=_quantity(row['value'])
            uncertainty={'kind':row['uncertainty_kind'],'description':row['uncertainty_description'],'value':_quantity(row['uncertainty_value']),'unit':row['uncertainty_unit'] or None}
            assumption=row['assumption'] or None
            if assumption is not None and not assumption.strip() or row['kind'] in {'model_input','assumption'} and assumption is None:
                raise ValueError('Substantive explicit model/assumption text required.')
            if assumption is not None:result['assumptions']=list(dict.fromkeys(result['assumptions']+[assumption]))
            item={'id':row['evidence_id'],'source':{**source,'locator':locator+'#sheet='+quote(p['sheet_name'],safe='')+'&row='+str(index)},
                'method':method,'period':period,'unit':row['unit'],'boundary_id':row['boundary_id'],'geography':row['geography'],'quality':quality,
                'assumption':assumption,'uncertainty':uncertainty,'calculation':{'formula':'Select complete source record from exact pinned workbook and named sheet','inputs':[document_id],'conversions':[],'rounding':'Original cell literal retained'}}
            validate_shape('evidence.schema.json',item);evidence.append(item)
            metrics.append({'id':row['metric_id'],'name':row['name'],'value':value,'unit':row['unit'],'period':period,'boundary_id':row['boundary_id'],
                'evidence_ids':[row['evidence_id']],'method':method,'assumption':assumption,'uncertainty':uncertainty,
                'calculation':{'formula':'Parse supplied literal cell; preserve declared unit/period/boundary','inputs':[row['evidence_id']],'conversions':[],'rounding':'Original literal retained in WORKBOOK_ROW_SOURCE; finite JSON-number representation'}})
            snapshots.append({'row':copy.deepcopy(row),**location,'kind_authenticated':False})
            if value is None:result['data_gaps'].append({'id':p['result_id']+'-missing-'+str(index),'field':row['metric_id'],'reason':'Blank source quantity remains null.',
                'impact':'No zero or estimated quantity inferred.','remedy':'Obtain a defensible source value or retain unknown.'})
        document={'id':document_id,'source':source,'method':method,'period':{'start':min(r['period_start'] for r in rows),'end':max(r['period_end'] for r in rows)},
            'unit':'mixed declared row units','boundary_id':state['organizational_boundary']['id'],'geography':'; '.join(sorted({r['geography'] for r in rows})),
            'quality':quality,'assumption':None,'uncertainty':{'kind':'unquantified','description':'Source/worksheet completeness and authenticity unverified.','value':None,'unit':None},'calculation':None}
        validate_shape('evidence.schema.json',document);additions=[document,*evidence];result['metrics']=metrics;result['evidence_ids']=[e['id'] for e in additions]
        result['review_requirements'].append({'id':p['result_id']+'-source-review','state':'PROFESSIONAL_REVIEW_REQUIRED',
            'reason':'Review workbook/cell provenance, measurement/model roles, source dates/units and domain/organization coverage before reliance.',
            'scope':meta['title'],'reviewer_role':'Qualified source/data reviewer','status':'open','resolution':None})
        result['data_gaps'].append({'id':p['result_id']+'-source-gap','field':'business_source_fitness','reason':'Byte/cell identity does not authenticate publisher, measurement fitness or organization completeness.',
            'impact':'Imported records remain qualified candidates.','remedy':'Obtain independent source and domain review.'})
        report={'execution_contract':CONTRACT,'file_pin':copy.deepcopy(pin),'source_metadata':copy.deepcopy(meta),'sheet_name':p['sheet_name'],
            'raw_byte_count':len(raw),'package':package,'rows':snapshots,'raw_business_data_ingestion_performed':True,
            'formula_evaluation_performed':False,'source_authenticity_verified':False,'organization_coverage_authenticated':False,'emission_factors_created':False,'publication_authorized':False}
        result['diagnostics'].append({'code':'WORKBOOK_ROW_SOURCE','message':json.dumps(report,sort_keys=True)})
    except (ValueError,TypeError,KeyError,OSError,zipfile.BadZipFile,ET.ParseError,ValidationError,UnicodeError,RuntimeError,zlib.error) as error:
        result=_empty(state,'normalize-sustainability-data',p['result_id']);result['status']='blocked';additions=[]
        result['diagnostics'].append({'code':'BUSINESS_WORKBOOK_SOURCE_REQUIRED','message':str(error)})
        result['data_gaps'].append({'id':p['result_id']+'-input-gap','field':'business_workbook_source','reason':str(error),
            'impact':'No partial workbook, assumptions, quantities or evidence imported.','remedy':'Reconcile exact bounded literal source and explicit sheet/schema.'})
    result['review_states']=list(dict.fromkeys(result['review_states']+[r['state'] for r in result['review_requirements'] if r['status']=='open']+['EVIDENCE_INCOMPLETE']))
    result['diagnostics'].append({'code':'BUSINESS_INGESTION_INPUTS','message':json.dumps(p,sort_keys=True)})
    result['next_actions']=['Review exact source/cell/period/unit/model and domain fitness; provide emission factors separately when needed.']
    return {'result':result,'proposal':propose(state,result,'Ingest exact literal workbook records with qualified source custody',additions)}
