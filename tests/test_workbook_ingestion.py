import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile
from scripts.contract_validation import ROOT,validate_state
from scripts.jurisdiction_tasks import _diagnostic
from scripts.workbook_ingestion import S,ingest_business_xlsx,read_literal_workbook
from tests.test_business_ingestion import ingestion_fixture


def workbook_fixture():
    state,p,manager=ingestion_fixture();path='data/inputs/fictional-business-records.xlsx';raw=(ROOT/path).read_bytes()
    p['file_pin'].update(path=path,sha256=hashlib.sha256(raw).hexdigest(),source_version='fictional-workbook-1')
    p['sheet_name']='Records';return state,p,manager


def altered(mutator):
    original=(ROOT/'data/inputs/fictional-business-records.xlsx').read_bytes()
    with zipfile.ZipFile(io.BytesIO(original)) as z:parts={name:z.read(name) for name in z.namelist()}
    mutator(parts);stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
        for name,raw in parts.items():z.writestr(name,raw)
    return stream.getvalue()


def sheet_change(parts,change):
    root=ET.fromstring(parts['xl/worksheets/sheet1.xml']);change(root);parts['xl/worksheets/sheet1.xml']=ET.tostring(root,encoding='utf-8')


class WorkbookIngestionTests(unittest.TestCase):
    def modified_output(self,raw):
        state,p,_=workbook_fixture()
        with tempfile.TemporaryDirectory() as d:
            workspace=Path(d);folder=workspace/'data/inputs';folder.mkdir(parents=True)
            path=folder/'source.xlsx';path.write_bytes(raw);p['file_pin'].update(path='data/inputs/source.xlsx',sha256=hashlib.sha256(raw).hexdigest())
            with patch('scripts.workbook_ingestion.ROOT',workspace):return state,p,ingest_business_xlsx(state,p)

    def test_exported_source_values_units_iso_text_and_cell_lineage(self):
        state,p,_=workbook_fixture();saved=copy.deepcopy(state);out=ingest_business_xlsx(state,p);r=_diagnostic(out['result'],'WORKBOOK_ROW_SOURCE')
        self.assertEqual(out['result']['status'],'partial');self.assertEqual(len(out['result']['metrics']),18)
        self.assertEqual([(m['value'],m['unit']) for m in out['result']['metrics'][:3]],[(1000,'kWh'),(0.6,'t'),(300,'kg')])
        self.assertEqual(r['rows'][0]['worksheet_row'],2);self.assertIn('ignore reviews',r['rows'][0]['row']['notes'])
        self.assertEqual(r['rows'][0]['cells'][4]['cell'],'E2');self.assertEqual(r['rows'][0]['cells'][4]['literal_v'],'1000')
        self.assertEqual(r['rows'][0]['row']['period_start'],'2025-01-01')
        self.assertFalse(r['formula_evaluation_performed']);self.assertFalse(r['source_authenticity_verified']);self.assertFalse(r['emission_factors_created'])
        self.assertEqual(state,saved);self.assertEqual(out['proposal']['state']['revision'],state['revision']+1);validate_state(out['proposal']['state'])
        document=p['document_evidence_id'];row=next(e for e in out['proposal']['state']['evidence'] if e['id']=='ev-001')
        self.assertEqual(row['calculation']['inputs'],[document]);self.assertIn('#sheet=Records&row=2',row['source']['locator'])

    def test_formula_with_cached_value_never_imported_and_whole_workbook_rolls_back(self):
        raw=altered(lambda parts:sheet_change(parts,lambda root:ET.SubElement(root.find('.//'+S+'c[@r="E19"]'),S+'f').__setattr__('text','100+200')))
        state,p,out=self.modified_output(raw)
        self.assertEqual(out['result']['status'],'blocked');self.assertEqual(out['result']['metrics'],[])
        self.assertEqual(out['proposal']['state']['evidence'],state['evidence']);self.assertEqual(out['proposal']['state']['assumptions'],state['assumptions'])
        self.assertTrue(any('Formulas' in d['message'] for d in out['result']['diagnostics']))

    def test_numeric_date_hidden_rows_merge_and_extra_columns_rejected(self):
        changes=[lambda root:root.find('.//'+S+'c[@r="G2"]').set('t','n'),
                 lambda root:root.find('.//'+S+'row[@r="2"]').set('hidden','1'),
                 lambda root:ET.SubElement(root,S+'mergeCells'),
                 lambda root:root.find('.//'+S+'c[@r="Q2"]').set('r','R2')]
        for change in changes:
            _,_,out=self.modified_output(altered(lambda parts:sheet_change(parts,change)))
            self.assertEqual(out['result']['status'],'blocked')

    def test_external_relationship_macros_package_escape_and_entities_block(self):
        def external(parts):
            root=ET.fromstring(parts['xl/_rels/workbook.xml.rels']);node=list(root)[0];node.set('TargetMode','External');node.set('Target','https://example.invalid/source')
            parts['xl/_rels/workbook.xml.rels']=ET.tostring(root,encoding='utf-8')
        changes=[external,lambda p:p.update({'xl/vbaProject.bin':b'not executed'}),lambda p:p.update({'../escape.xml':b'<x/>'}),
                 lambda p:p.update({'xl/worksheets/sheet1.xml':b'<!DOCTYPE x [<!ENTITY a "boom">]><x/>'})]
        for change in changes:
            _,_,out=self.modified_output(altered(change));self.assertEqual(out['result']['status'],'blocked')

    def test_blank_zero_negative_and_model_assumptions_retained(self):
        def blank(root):root.find('.//'+S+'c[@r="E2"]').find(S+'v').text=''
        _,_,out=self.modified_output(altered(lambda p:sheet_change(p,blank)));self.assertIsNone(out['result']['metrics'][0]['value'])
        self.assertTrue(any(g['field']=='metric-001' for g in out['result']['data_gaps']))
        for value in ('0','-2'):
            _,_,out=self.modified_output(altered(lambda p:sheet_change(p,lambda root:root.find('.//'+S+'c[@r="E2"]').find(S+'v').__setattr__('text',value))))
            self.assertEqual(out['result']['metrics'][0]['value'],float(value))
        state,p,_=workbook_fixture();out=ingest_business_xlsx(state,p)
        self.assertTrue(next(m for m in out['result']['metrics'] if m['id']=='discount')['assumption'])

    def test_invalid_numeric_values_duplicates_or_wrong_headers_block(self):
        for value in ('NaN','1,000','1e999','1e-999',' 1 '):
            _,_,out=self.modified_output(altered(lambda p:sheet_change(p,lambda root:root.find('.//'+S+'c[@r="E2"]').find(S+'v').__setattr__('text',value))))
            self.assertEqual(out['result']['status'],'blocked',value)
        for address,value in (('A3','row-1'),('A1','wrong_header')):
            _,_,out=self.modified_output(altered(lambda p:sheet_change(p,lambda root:root.find('.//'+S+'c[@r="'+address+'"]').find(S+'v').__setattr__('text',value))))
            self.assertEqual(out['result']['status'],'blocked')

    def test_sheet_selection_hash_size_and_fixture_gates(self):
        for change in ('sheet','hash','fixture'):
            state,p,_=workbook_fixture()
            if change=='sheet':p['sheet_name']='Other'
            elif change=='hash':p['file_pin']['sha256']='0'*64
            else:p['fixture_mode']=False
            self.assertEqual(ingest_business_xlsx(state,p)['result']['status'],'blocked')
        state,p,_=workbook_fixture();p['file_pin']['synthetic']=False
        self.assertEqual(ingest_business_xlsx(state,p)['result']['status'],'blocked')
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as z:
            z.writestr('large.xml',b'x'*2097153)
        with self.assertRaises(ValueError):read_literal_workbook(stream.getvalue(),'Records')

    def test_shared_and_inline_strings_preserve_text(self):
        def shared(parts):
            root=ET.fromstring(parts['xl/worksheets/sheet1.xml']);cell=root.find('.//'+S+'c[@r="A1"]');cell.set('t','s');cell.find(S+'v').text='0'
            table=ET.Element(S+'sst');si=ET.SubElement(table,S+'si');ET.SubElement(si,S+'t').text='record_id';parts['xl/sharedStrings.xml']=ET.tostring(table,encoding='utf-8');parts['xl/worksheets/sheet1.xml']=ET.tostring(root,encoding='utf-8')
        _,_,out=self.modified_output(altered(shared));self.assertEqual(out['result']['status'],'partial')
        def inline(root):
            cell=root.find('.//'+S+'c[@r="A1"]');cell.remove(cell.find(S+'v'));cell.set('t','inlineStr');item=ET.SubElement(cell,S+'is');ET.SubElement(item,S+'t').text='record_id'
        _,_,out=self.modified_output(altered(lambda p:sheet_change(p,inline)));self.assertEqual(out['result']['status'],'partial')

    def test_actual_cli_equals_helper_and_request_and_workbook_unchanged(self):
        state,p,_=workbook_fixture();r={'contract_version':'0.1.0','skill':'ingest-business-records','state':state,'parameters':p};raw=json.dumps(r).encode();file=ROOT/p['file_pin']['path'];original=file.read_bytes()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'request.json';path.write_bytes(raw)
            cli=subprocess.run([sys.executable,'-m','scripts.run_workbook_ingestion',str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(cli.returncode,0,cli.stdout+cli.stderr);self.assertEqual(json.loads(cli.stdout),ingest_business_xlsx(state,p));self.assertEqual(path.read_bytes(),raw)
        self.assertEqual(file.read_bytes(),original)

    def test_wrong_workbook_content_type_and_relationship_namespace_block(self):
        def content(parts):
            root=ET.fromstring(parts['[Content_Types].xml'])
            ET.SubElement(root,'{http://schemas.openxmlformats.org/package/2006/content-types}Override',{'PartName':'/xl/workbook.xml','ContentType':'application/pdf'})
            parts['[Content_Types].xml']=ET.tostring(root,encoding='utf-8')
        def relations(parts):parts['xl/_rels/workbook.xml.rels']=parts['xl/_rels/workbook.xml.rels'].replace(b'http://schemas.openxmlformats.org/package/2006/relationships',b'urn:unsupported')
        for change in (content,relations):
            _,_,out=self.modified_output(altered(change));self.assertEqual(out['result']['status'],'blocked')

    def test_duplicate_cells_and_ambiguous_cell_representations_block(self):
        def duplicate(root):
            row=root.find('.//'+S+'row[@r="2"]');row.append(copy.deepcopy(row.find(S+'c')))
        def conflicting(root):ET.SubElement(root.find('.//'+S+'c[@r="E2"]'),S+'is')
        for change in (duplicate,conflicting):
            _,_,out=self.modified_output(altered(lambda p:sheet_change(p,change)));self.assertEqual(out['result']['status'],'blocked')
