"""Write a machine-readable provenance record after a completed model run."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess


SOURCE_FILES = (
    'run_urban_mental_health.py',
    'urban_mental_health_tasks.py',
    'urban_mental_health_functions.py',
    'effect_size_uncertainty.py',
    'cost_basis.py',
    'run_provenance.py',
    'environment.yml',
)


def file_record(path):
    """Return a path, byte count, and streaming SHA-256 for one existing file."""
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError(f'Expected a file: {path}')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    return {'path': str(path), 'size_bytes': path.stat().st_size, 'sha256': digest.hexdigest()}


def git_head(source_dir):
    """Record the exact commit when this source directory is a Git checkout."""
    result = subprocess.run(
        ['git', '-C', str(source_dir), 'rev-parse', 'HEAD'],
        capture_output=True, text=True, check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def write_manifest(project_dir, inputs, source_dir, outputs, parameters):
    """Hash input, source, and output files and write run_manifest.json."""
    project_dir = Path(project_dir).expanduser().resolve()
    source_dir = Path(source_dir).expanduser().resolve()
    manifest = {
        'completed_at_utc': datetime.now(timezone.utc).isoformat(),
        'git_commit': git_head(source_dir),
        'python': platform.python_version(),
        'parameters': parameters,
        'inputs': {name: file_record(path) for name, path in inputs.items()},
        'source_files': {name: file_record(source_dir / name) for name in SOURCE_FILES},
        'outputs': {name: file_record(path) for name, path in outputs.items()},
    }
    project_dir.mkdir(parents=True, exist_ok=True)
    target = project_dir / 'run_manifest.json'
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return target
