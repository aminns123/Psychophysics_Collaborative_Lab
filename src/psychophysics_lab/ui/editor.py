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
    if not code and os.name=='nt': code=shutil.which('notepad')
    if not code: raise FileNotFoundError('No external text editor was found. Configure an editor executable or open the displayed file path manually.')
    # Folder identity lets VS Code match the project. --reuse-window alone can
    # repurpose an unrelated last-active window, so deliberately omit that flag.
    if Path(code).stem.lower() not in {"code", "code-insiders"}:
        return [code,str(path)]
    return [code,str(root),'--goto',f'{path}:{line}']

def open_source(repo_root: Path, source: Path, line: int = 1, executable: str | None = None):
    return subprocess.Popen(editor_command(repo_root,source,line,executable),cwd=repo_root,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


def open_parameter_file(repo_root: Path, path: Path, config_root: Path, executable=None, *, allow_external_existing=False, line=1):
    """Open an actual local JSON file in Code or the configured text editor.

    These are working configuration files, outside source and participant data.
    Paths are arguments, never shell command text. No editor is embedded here.
    """
    if isinstance(line, bool) or not isinstance(line, int) or line < 1:
        raise ValueError("Source line must be a positive integer.")
    path, allowed = Path(path).resolve(), Path(config_root).resolve()
    if (not path.is_relative_to(allowed) and not allow_external_existing) or not path.is_file() or path.suffix.lower() != ".json":
        raise ValueError("Open an existing parameter JSON inside local configuration.")
    editor = executable or shutil.which("code")
    if editor and Path(editor).suffix.lower() in {".cmd", ".bat"}:
        candidate = Path(editor).parent.parent/"Code.exe"
        editor = str(candidate) if candidate.is_file() else None
    if not editor and os.name == "nt":
        candidate = Path(os.environ.get("LOCALAPPDATA", ""))/"Programs"/"Microsoft VS Code"/"Code.exe"
        editor = str(candidate) if candidate.is_file() else shutil.which("notepad")
    if not editor:
        raise FileNotFoundError(f"No external editor found. Open this file in your editor: {path}")
    is_code = Path(editor).stem.lower() in {"code", "code-insiders"}
    command = [editor, str(Path(repo_root).resolve()), "--goto", f"{path}:{line}"] if is_code else [editor, str(path)]
    return subprocess.Popen(command, cwd=repo_root, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
