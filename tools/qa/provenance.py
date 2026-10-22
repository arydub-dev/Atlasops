"""Content identity for explicitly selected source files; never reads runtime secrets."""
import hashlib
import json
import subprocess
from pathlib import Path

DIRECTORIES = ('backend/app', 'backend/alembic', 'backend/tests', 'frontend/app',
               'frontend/components', 'frontend/lib', 'frontend/hooks', 'frontend/qa',
               'tools/qa', 'tools/recovery')
EXTENSIONS = {'.py', '.ts', '.tsx', '.js', '.mjs', '.json', '.css', '.ini'}
CONFIGS = ('backend/requirements.txt', 'backend/pyproject.toml', 'backend/alembic.ini',
           'frontend/package.json', 'frontend/package-lock.json', 'frontend/tsconfig.json',
           'frontend/next.config.ts', 'frontend/next.config.js', 'frontend/next.config.mjs',
           'vercel.json', 'api/index.py')


def snapshot(root):
    root = Path(root)
    paths = set()
    for folder in DIRECTORIES:
        for p in (root / folder).rglob('*'):
            if p.is_file() and not p.is_symlink() and p.suffix in EXTENSIONS and not any(
                x.startswith('.') or x in ('node_modules', '__pycache__') for x in p.relative_to(root).parts
            ):
                paths.add(p)
    paths.update(root / p for p in CONFIGS if (root / p).is_file() and not (root / p).is_symlink())
    files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    git = {'revision': None, 'dirty': None, 'status': 'UNVERIFIED'}
    try:
        revision = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], stderr=subprocess.DEVNULL, text=True).strip())
        git = {'revision': revision, 'dirty': dirty, 'status': 'OBSERVED'}
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return {'schema_version': 1, 'git': git, 'source_sha256': digest, 'files': files,
            'scope': 'Allowlisted application, migration, tests and QA source/config; not a Git commit or complete repository archive. Runtime secrets, dependencies, reports and generated files excluded.'}
