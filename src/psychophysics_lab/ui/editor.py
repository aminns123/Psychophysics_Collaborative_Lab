"""Open real source with explicit project context, without shell interpolation."""
import os
from pathlib import Path
import shutil
import subprocess

def editor_command(repo_root: Path, source: Path, line: int = 1, executable: str | None = None):
    root=repo_root.resolve(); path=source.resolve()
    if not path.is_relative_to(root) or not path.is_file(): raise ValueError('Source must be an existing file in this project.')
    if isinstance(line,bool) or not isinstance(line,int) or line<1: raise ValueError('Source line must be positive.')
    code=executable or shutil.which('code')
    # Launch Code.exe directly on Windows, avoiding cmd.exe metacharacter rules.
    if code and Path(code).suffix.lower() in {'.cmd','.bat'}:
        candidate=Path(code).parent.parent/'Code.exe'
        code=str(candidate) if candidate.is_file() else None
    if not code and os.name=='nt':
        candidate=Path(os.environ.get('LOCALAPPDATA',''))/'Programs'/'Microsoft VS Code'/'Code.exe'
        code=str(candidate) if candidate.is_file() else None
    if not code: raise FileNotFoundError('VS Code was not found. Install its command-line launcher or configure a Code executable.')
    # Folder identity lets VS Code match the project. --reuse-window alone can
    # repurpose an unrelated last-active window, so deliberately omit that flag.
    return [code,str(root),'--goto',f'{path}:{line}']

def open_source(repo_root: Path, source: Path, line: int = 1, executable: str | None = None):
    return subprocess.Popen(editor_command(repo_root,source,line,executable),cwd=repo_root,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
