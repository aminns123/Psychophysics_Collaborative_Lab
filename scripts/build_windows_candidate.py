"""Maintainer-only private candidate builder; no publish/release/signing operation.

Students receive an authorised setup package, not these build commands. Rights
clearance and authenticated delivery remain required before redistribution.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact(record, cache, download):
    if Path(record['filename']).name != record['filename']:
        raise ValueError('Artifact filename must not contain a path.')
    path = cache / record['filename']
    if not path.exists():
        if not download:
            raise ValueError(f"Missing reviewed artifact: {path.name}; obtain it from its pinned publisher URL.")
        cache.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + '.partial')
        urllib.request.urlretrieve(record.get('source', record.get('url')), temporary)
        if sha(temporary) != record['sha256']:
            raise ValueError(f"Publisher hash mismatch: {path.name}")
        temporary.replace(path)
    if path.is_symlink() or sha(path) != record['sha256']:
        raise ValueError(f"Artifact is altered: {path.name}")
    return path


def build(output, cache, label, download=False, *, compiler=None):
    output, cache = Path(output).resolve(), Path(cache).resolve()
    if output.exists():
        raise ValueError('Choose a new candidate folder; existing folders are never overwritten.')
    if output.is_relative_to(ROOT) or cache.is_relative_to(output) or output.is_relative_to(cache):
        raise ValueError('Keep candidate, source and artifact-cache folders separate.')
    profile_dir = ROOT / 'requirements/windows-cp311'
    profile = json.loads((profile_dir / 'profile.json').read_text(encoding='utf-8'))
    for name, digest in profile['files'].items():
        if Path(name).name != name or sha(profile_dir / name) != digest:
            raise ValueError('Reviewed profile file changed: ' + name)
    bootstrap = json.loads((ROOT / 'packaging/windows/bootstrap.json').read_text(encoding='utf-8'))
    native = json.loads((profile_dir / 'interpreter-artifacts.json').read_text(encoding='utf-8'))
    # Verify all input bytes before allocating a candidate folder.
    container = artifact(bootstrap['container'], cache, download)
    try:
        from conda_package_handling.api import extract
    except ImportError as exc:
        raise ValueError('Maintainer builds require conda-package-handling from the build toolchain; students do not.') from exc
    with tempfile.TemporaryDirectory(prefix='psycolab-provisioner-') as temp:
        extract(str(container), dest_dir=temp)
        executable = Path(temp) / 'standalone_conda/conda.exe'
        if sha(executable) != bootstrap['sha256']:
            raise ValueError('The standalone provisioner differs from its reviewed payload.')
        shutil.copyfile(executable, cache / bootstrap['filename'])
        notices = Path(temp) / 'info/licenses'
        for notice in notices.rglob('*'):
            if notice.is_file():
                target = cache / 'provisioner-licenses' / notice.relative_to(notices)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(notice, target)
    artifacts = [('tools/' + bootstrap['filename'], artifact(bootstrap, cache, False))]
    artifacts += [('tools/licenses/' + p.relative_to(cache / 'provisioner-licenses').as_posix(), p)
                  for p in (cache / 'provisioner-licenses').rglob('*') if p.is_file()]
    artifacts += [('interpreter/' + item['filename'], artifact(item, cache, download)) for item in native]
    wheels = [record for name, record in profile['artifacts'].items() if name in profile['core']]
    artifacts += [('wheels/' + item['filename'], artifact(item, cache, download)) for item in wheels]
    compiler = compiler or Path('C:/Windows/Microsoft.NET/Framework64/v4.0.30319/csc.exe')
    if not compiler.is_file():
        raise ValueError('The Windows .NET Framework C# compiler is required by the maintainer builder.')
    files = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    files = [name for name in files if name]
    # No ignored pointers, environments, laboratory roots or personal files enter a package.
    if any(name.startswith(('.venv/', '.venv-dev/', 'USER_env/')) or name == '.psycolab_local.json' for name in files):
        raise ValueError('Protected local files must not be tracked or packaged.')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT))
    output.mkdir(parents=True)
    for relative, path in artifacts:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
    source_files = {}
    for name in files:
        source = ROOT / name
        if source.is_symlink() or not source.is_file():
            raise ValueError('Only ordinary reviewed source files can be packaged: ' + name)
        dest = output / 'source' / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
        source_files[name] = sha(dest)
    (output / 'CANDIDATE_NOT_FOR_DISTRIBUTION.txt').write_text(
        'Private qualification candidate. No public redistribution is authorised.\n'
        'See source/docs/WINDOWS_GUIDED_INSTALLATION.md and licensing checklist.\n', encoding='utf-8')
    inventory = {p.relative_to(output).as_posix(): sha(p) for p in output.rglob('*') if p.is_file()}
    identity = hashlib.sha256(json.dumps(inventory, sort_keys=True).encode()).hexdigest()
    manifest = dict(schema_version=1, id=identity, label=label, source_commit=revision,
                    source_dirty=dirty, distribution_allowed=False, profile_id=profile['id'],
                    files=inventory, source_files=source_files,
                    interpreter_files=['interpreter/' + item['filename'] for item in native],
                    wheel_probe=wheels[0]['filename'])
    (output / 'bundle.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    # Embed the exact inventory in the host. Its own bytes are outside the inventory
    # to avoid a circular hash; a signed/trusted host authenticates the inventory.
    command = [str(compiler), '/nologo', '/codepage:65001', '/target:winexe', '/platform:x64',
               '/r:System.Windows.Forms.dll', '/r:System.Drawing.dll', '/r:System.Web.Extensions.dll',
               '/r:Microsoft.CSharp.dll', '/out:' + str(output / 'PsyCoLabSetup.exe'),
               '/resource:' + str(output / 'bundle.json') + ',PsyCoLab.Bundle',
               str(ROOT / 'packaging/windows/GuidedSetup.cs')]
    subprocess.run(command, cwd=ROOT, check=True)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--label', required=True)
    parser.add_argument('--download-reviewed', action='store_true')
    args = parser.parse_args()
    print(build(args.output, args.cache, args.label, args.download_reviewed))
