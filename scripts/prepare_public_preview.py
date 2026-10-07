"""Build a local, explicitly limited preview; never publish or grant a license."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINTS = ('scripts/data_tools.py', 'scripts/run_energy.py',
                'scripts/run_water.py', 'scripts/run_resources.py', 'scripts/run_finance.py')


def source_closure():
    """Collect repository Python dependencies without executing imports."""
    pending = list(ENTRY_POINTS)
    found = set()
    while pending:
        name = pending.pop()
        if name in found:
            continue
        path = ROOT / name
        if not path.is_file():
            raise ValueError('Missing preview dependency: ' + name)
        found.add(name)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
            if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module:
                pending.append('scripts/' + node.module.replace('.', '/') + '.py')
            elif isinstance(node, ast.ImportFrom) and node.level > 1:
                raise ValueError('Unsupported relative import in preview closure')
    return sorted(found)


def prepare(output):
    output = output.resolve()
    private = (ROOT / 'private-data/public-preview').resolve()
    if not output.is_relative_to(private):
        raise ValueError('Output must stay under ignored private-data/public-preview')
    if output.exists():
        raise ValueError('Use a fresh output directory; existing artifacts are preserved')
    selected = source_closure()
    selected += sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'schemas').glob('*.schema.json'))
    selected += sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'wiki').glob('*.md'))
    selected += ['requirements-dev.txt', 'docs/public-preview.md', 'docs/preview-distribution-status.md',
                 'examples/preview-conversion.json']
    # Explicit surface: no standards, research, historical captures, customer data,
    # Git history, funding/account metadata, virtual environments or private archives.
    allowed = ('scripts/', 'schemas/', 'wiki/', 'docs/', 'examples/')
    assert all(n == 'requirements-dev.txt' or n.startswith(allowed) for n in selected)
    files = {}
    for name in selected:
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise ValueError('Unsafe/missing preview path')
        target = {'docs/public-preview.md': 'README.md',
                  'docs/preview-distribution-status.md': 'DISTRIBUTION-STATUS.md',
                  'requirements-dev.txt': 'requirements.txt'}.get(name, name)
        raw = path.read_bytes()
        if name == 'docs/public-preview.md':
            raw = raw.replace(b'](preview-distribution-status.md)', b'](DISTRIBUTION-STATUS.md)')
            raw = raw.replace(b'](../wiki/Home.md)', b'](wiki/Home.md)')
        files[target] = raw
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    manifest = {'preview_version': '0.1.0-draft', 'source_revision': revision,
                'publication_authorized': False, 'license_selected': False,
                'public_v1_readiness': False, 'scope': 'Selected original neutral arithmetic helpers and shared schemas; no standards/jurisdiction catalogs or agent skill installation',
                'entry_points': list(ENTRY_POINTS),
                'excluded': ['standards/**', 'evaluations/**', 'data/**', 'private-data/**', '.git/**', '.github/**', 'skills/**', 'skillsets/**', 'router/**'],
                'files': {n: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} for n, raw in sorted(files.items())}}
    files['PREVIEW-MANIFEST.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    output.mkdir(parents=True)
    for name, raw in files.items():
        destination = output / 'tree' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
    archive = output / 'AgentSustain-preview-0.1.0-draft.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
        for name, raw in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 6, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            package.writestr(info, raw)
    receipt = {'archive': archive.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
               'files': len(files), 'source_revision': revision, 'publication_authorized': False,
               'license_selected': False, 'public_v1_readiness': False}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    print(json.dumps(prepare(parser.parse_args().output), indent=2))
