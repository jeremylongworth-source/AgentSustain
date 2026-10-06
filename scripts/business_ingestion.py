"""Pinned UTF-8 CSV ingestion with literal values and append-only row evidence."""
import copy
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import io
from itertools import islice
import json
import math
import re
from jsonschema import ValidationError

from .contract_validation import ROOT, validate_state, validate_shape
from .state_proposal import propose


HEADERS = ['record_id', 'evidence_id', 'metric_id', 'name', 'value', 'unit', 'period_start', 'period_end', 'boundary_id',
           'geography', 'kind', 'assumption', 'uncertainty_kind', 'uncertainty_description', 'uncertainty_value', 'uncertainty_unit', 'notes']
INPUT_ROOT = ROOT / 'data/inputs'


def _quantity(text):
    if text == '': return None
    if text.strip() != text: raise ValueError('Numeric cells cannot hide whitespace or locale separators.')
    if not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', text):
        raise ValueError('Only explicit ASCII decimal/scientific notation is supported.')
    try: number = Decimal(text)
    except InvalidOperation as error: raise ValueError('A decimal quantity or empty unknown cell is required.') from error
    if not number.is_finite(): raise ValueError('NaN and infinite quantities are unsupported.')
    value = float(number)
    if not math.isfinite(value) or number != 0 and value == 0:
        raise ValueError('Quantity cannot be represented without overflow or false zero.')
    return value


def ingest_business_csv(state, parameters):
    validate_state(state)
    fields = {'file_pin', 'source_metadata', 'fixture_mode', 'result_id', 'document_evidence_id'}
    classified = isinstance(parameters, dict) and 'source_classification_review' in parameters
    if not isinstance(parameters, dict) or set(parameters) != fields | ({'source_classification_review'} if classified else set()):
        raise ValueError('Exact CSV ingestion parameters required.')
    ident = parameters['result_id']; document_id = parameters['document_evidence_id']
    if not all(isinstance(v, str) and v.strip() for v in (ident, document_id)) or type(parameters['fixture_mode']) is not bool:
        raise ValueError('Explicit IDs and boolean fixture mode required.')
    if any(r['id'] == ident for r in state['results']): raise ValueError('Result ID must be fresh.')
    result = {'id': ident, 'skill': 'normalize-sustainability-data', 'contract_version': '0.1.0', 'status': 'partial',
        'review_states': list(dict.fromkeys(['ADVISORY', 'EVIDENCE_INCOMPLETE'] + [r['state'] for r in state['review_requirements'] if r['status'] == 'open'])),
        'review_requirements': copy.deepcopy(state['review_requirements']), 'metrics': [], 'evidence_ids': [],
        'assumptions': list(state['assumptions']), 'data_gaps': copy.deepcopy(state['data_gaps']), 'diagnostics': [], 'next_actions': []}
    additions = []
    try:
        pin = parameters['file_pin']; meta = parameters['source_metadata']
        if not isinstance(pin, dict) or set(pin) != {'path', 'sha256', 'source_version', 'synthetic'}:
            raise ValueError('Exact file path/hash/version/synthetic pin required.')
        if not isinstance(meta, dict) or set(meta) != {'title', 'publisher', 'accessed', 'tier'}:
            raise ValueError('Explicit source title/publisher/access date/tier required.')
        if not all(isinstance(meta[k], str) and meta[k].strip() for k in ('title', 'publisher', 'accessed')):
            raise ValueError('Source identity/date declarations cannot be blank.')
        if (type(pin['synthetic']) is not bool or not isinstance(pin['source_version'], str) or not pin['source_version'].strip()
            or not isinstance(pin['path'], str) or not pin['path'].startswith('data/inputs/') or '\\' in pin['path']):
            raise ValueError('Versioned workspace CSV with explicit synthetic status required.')
        path = ROOT / pin['path']
        if '..' in path.parts or not path.resolve().is_relative_to(INPUT_ROOT.resolve()) or path.suffix.lower() != '.csv':
            raise ValueError('CSV path must stay inside data/inputs.')
        if pin['synthetic'] and not parameters['fixture_mode']: raise ValueError('Synthetic files cannot enter ordinary-use mode.')
        if not path.is_file() or path.stat().st_size > 1048576: raise ValueError('Existing CSV up to 1 MiB required.')
        raw = path.read_bytes()
        if len(raw) > 1048576 or hashlib.sha256(raw).hexdigest() != pin['sha256']: raise ValueError('CSV bytes differ from the selected pin.')
        if not pin['synthetic']:
            # Repository examples use this reserved prefix. Byte copies retain synthetic status.
            fixtures = list(islice(INPUT_ROOT.glob('fictional-*.csv'), 65))
            if len(fixtures) > 64:
                raise ValueError('Recognized-fixture lookup exceeds its bounded file count.')
            total = 0
            for shipped in sorted(fixtures):
                if not shipped.is_file():
                    continue
                size = shipped.stat().st_size
                total += size
                if (not shipped.resolve().is_relative_to(INPUT_ROOT.resolve())
                    or size > 1048576 or total > 8388608):
                    raise ValueError('Recognized-fixture lookup must remain bounded inside data/inputs.')
                with shipped.open('rb') as fixture_source:
                    fixture_bytes = fixture_source.read(1048577)
                if len(fixture_bytes) > 1048576:
                    raise ValueError('Recognized-fixture lookup must remain bounded inside data/inputs.')
                if path.resolve() == shipped.resolve() or raw == fixture_bytes:
                    raise ValueError('The recognized fictional export cannot be relabeled ordinary data.')
        text = raw.decode('utf-8'); reader = csv.DictReader(io.StringIO(text, newline=''), strict=True)
        if reader.fieldnames != HEADERS: raise ValueError('Exact distinct CSV headers required; no inferred columns or units.')
        rows = []; end_lines = []
        for row in reader:
            rows.append(row); end_lines.append(reader.line_num)
        if not rows or len(rows) > 200: raise ValueError('Between 1 and 200 complete logical records required.')
        record_tiers = {}
        if classified:
            classification = parameters['source_classification_review']
            if (not isinstance(classification, dict) or set(classification) != {'record_tiers', 'basis', 'rationale', 'reviewer_role'}
                or not all(isinstance(classification[k], str) and classification[k].strip() for k in ('basis', 'rationale', 'reviewer_role'))
                or not isinstance(classification['record_tiers'], dict)
                or set(classification['record_tiers']) != {r['record_id'] for r in rows}
                or any(type(t) is not int or t not in range(1, 6) for t in classification['record_tiers'].values())):
                raise ValueError('Explicit complete per-record source tiers and attributed classification review required.')
            record_tiers = classification['record_tiers']
        known = {e['id'] for e in state['evidence']} | {m['id'] for r in state['results'] for m in r['metrics']}
        if document_id in known: raise ValueError('Document evidence ID must be fresh.')
        known.add(document_id); records = set(); snapshots = []; metrics = []; row_evidence = []
        locator = 'workspace:' + pin['path']; method = {'name': 'Pinned UTF-8 CSV decimal ingestion without unit conversion', 'version': '0.2.0' if classified else '0.1.0', 'source': locator}
        source = {**copy.deepcopy(meta), 'locator': locator, 'version': pin['source_version']}
        quality = {'reliability': 'unknown', 'completeness': 'unknown', 'fitness_notes': 'Exact source bytes and supplied row declarations; authenticity and organization coverage remain unverified.'}
        for index, row in enumerate(rows, 1):
            if set(row) != set(HEADERS) or any(v is None for v in row.values()): raise ValueError('Ragged or extra CSV cells are unsupported.')
            if any(not row[k].strip() for k in ('record_id', 'evidence_id', 'metric_id', 'name', 'unit', 'boundary_id', 'geography', 'uncertainty_description')):
                raise ValueError('Record/evidence/metric identities, names, units and uncertainty descriptions cannot be blank.')
            if row['record_id'] in records or row['evidence_id'] in known or row['metric_id'] in known or row['metric_id'] == row['evidence_id']:
                raise ValueError('Distinct fresh record/evidence/metric identities required; no overwrite or alias collision.')
            records.add(row['record_id']); known.update((row['evidence_id'], row['metric_id']))
            if row['boundary_id'] != state['organizational_boundary']['id'] or row['kind'] not in {'measurement', 'model_input', 'assumption', 'unknown'}:
                raise ValueError('Explicit current boundary and supported attributed record kind required.')
            start = date.fromisoformat(row['period_start']); end = date.fromisoformat(row['period_end'])
            if start > end: raise ValueError('Record period is reversed.')
            when = {'start': row['period_start'], 'end': row['period_end']}; value = _quantity(row['value'])
            uncertainty = {'kind': row['uncertainty_kind'], 'description': row['uncertainty_description'],
                           'value': _quantity(row['uncertainty_value']), 'unit': row['uncertainty_unit'] or None}
            assumption = row['assumption'] or None
            if assumption is not None and not assumption.strip(): raise ValueError('Assumption text cannot be whitespace.')
            if row['kind'] in {'model_input', 'assumption'} and assumption is None:
                raise ValueError('Model/assumption rows must state their assumptions; they are not observations.')
            if assumption is not None: result['assumptions'] = list(dict.fromkeys(result['assumptions'] + [assumption]))
            calculation = {'formula': 'Parse the supplied decimal cell; preserve its declared unit, period and boundary',
                           'inputs': [row['evidence_id']], 'conversions': [], 'rounding': 'Literal decimal retained in CSV_ROW_SOURCE; JSON finite-number representation'}
            evidence = {'id': row['evidence_id'], 'source': {**source, 'tier': record_tiers.get(row['record_id'], meta['tier']), 'locator': locator + '#record=' + str(index)}, 'method': method,
                'period': when, 'unit': row['unit'], 'boundary_id': row['boundary_id'], 'geography': row['geography'],
                'quality': quality, 'assumption': assumption, 'uncertainty': uncertainty,
                'calculation': {'formula': 'Select the complete logical CSV record from the pinned document', 'inputs': [document_id], 'conversions': [], 'rounding': 'No quantity conversion'}}
            validate_shape('evidence.schema.json', evidence)
            metric = {'id': row['metric_id'], 'name': row['name'], 'value': value, 'unit': row['unit'], 'period': when,
                'boundary_id': row['boundary_id'], 'evidence_ids': [row['evidence_id']], 'method': method,
                'assumption': assumption, 'uncertainty': uncertainty, 'calculation': calculation}
            row_evidence.append(evidence); metrics.append(metric)
            snapshots.append({'logical_record': index, 'physical_end_line': end_lines[index - 1], 'row': copy.deepcopy(row), 'kind_authenticated': False})
            if value is None:
                result['data_gaps'].append({'id': ident + '-missing-' + str(index), 'field': row['metric_id'], 'reason': 'Source quantity is blank; imported value remains null.',
                    'impact': 'No zero or estimated quantity is inferred.', 'remedy': 'Obtain a defensible source quantity or retain the unknown.'})
        document_period = {'start': min(r['period_start'] for r in rows), 'end': max(r['period_end'] for r in rows)}
        document = {'id': document_id, 'source': source, 'method': method, 'period': document_period, 'unit': 'mixed declared row units',
            'boundary_id': state['organizational_boundary']['id'], 'geography': '; '.join(sorted({row['geography'] for row in rows})), 'quality': quality, 'assumption': None,
            'uncertainty': {'kind': 'unquantified', 'description': 'Document authenticity, coverage and record-specific uncertainty remain unverified.', 'value': None, 'unit': None}, 'calculation': None}
        validate_shape('evidence.schema.json', document)
        additions = [document, *row_evidence]; result['metrics'] = metrics; result['evidence_ids'] = [e['id'] for e in additions]
        result['review_states'].append('PROFESSIONAL_REVIEW_REQUIRED')
        result['review_requirements'].append({'id': ident + '-source-review', 'state': 'PROFESSIONAL_REVIEW_REQUIRED',
            'reason': 'Review raw source authenticity, measurement/model roles, service definitions, units, periods, coverage and applicable methods.',
            'scope': meta['title'], 'reviewer_role': 'Qualified source/data reviewer', 'status': 'open', 'resolution': None})
        result['data_gaps'].append({'id': ident + '-source-gap', 'field': 'business_source_fitness', 'reason': 'Pinned byte/row identity does not authenticate publisher, measurement fitness or organization completeness.',
            'impact': 'Imported records remain qualified source candidates.', 'remedy': 'Obtain independent source and domain review before reliance.'})
        report = {'execution_contract': ('business-csv-ingestion-0.2.0' if classified else 'business-csv-ingestion-0.1.0'), 'file_pin': copy.deepcopy(pin), 'source_metadata': copy.deepcopy(meta),
            'raw_byte_count': len(raw), 'rows': snapshots, 'raw_business_data_ingestion_performed': True, 'source_authenticity_verified': False,
            'organization_coverage_authenticated': False, 'emission_factors_created': False, 'publication_authorized': False}
        if classified:
            report['source_classification_review'] = copy.deepcopy(classification)
            report['record_source_tiers_authenticated'] = False
        result['diagnostics'].append({'code': 'CSV_ROW_SOURCE', 'message': json.dumps(report, sort_keys=True)})
    except (ValueError, TypeError, KeyError, OSError, csv.Error, ValidationError) as error:
        result['status'] = 'blocked'; result['metrics'] = []; result['evidence_ids'] = []; additions = []
        result['assumptions'] = list(state['assumptions']); result['data_gaps'] = copy.deepcopy(state['data_gaps'])
        result['review_requirements'] = copy.deepcopy(state['review_requirements'])
        result['review_states'] = list(dict.fromkeys(['ADVISORY', 'EVIDENCE_INCOMPLETE'] + [r['state'] for r in state['review_requirements'] if r['status'] == 'open']))
        result['diagnostics'] = [{'code': 'BUSINESS_SOURCE_REQUIRED', 'message': str(error)}]
        result['data_gaps'].append({'id': ident + '-input-gap', 'field': 'business_source', 'reason': str(error),
            'impact': 'No partial file or unsupported quantity is imported.', 'remedy': 'Reconcile exact source bytes, declarations and unique row identities.'})
    result['diagnostics'].append({'code': 'BUSINESS_INGESTION_INPUTS', 'message': json.dumps(parameters, sort_keys=True)})
    result['next_actions'] = ['Review exact raw records and resolve source/domain requirements; register defensible factors separately when required.']
    return {'result': result, 'proposal': propose(state, result, 'Ingest exact pinned CSV records with qualified source custody', additions)}
