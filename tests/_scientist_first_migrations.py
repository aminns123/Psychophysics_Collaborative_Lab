"""Exact new sources and immutable pre-migration references for Waves 3–5."""
import hashlib
import json

def migration_reference(root, identity):
    for wave in (3, 4, 5):
        folder = root / "tests/fixtures" / ("issue165_wave" + str(wave))
        manifest = folder / "baseline.json"
        if not manifest.exists():
            continue
        saved = json.loads(manifest.read_text(encoding="utf-8"))
        assert saved["commit"] == "8f493fa0a54cbe57109943120b5e410e77c0541a"
        if identity not in saved["experiments"]:
            continue
        contract = saved["experiments"][identity]
        before = folder / (identity + ".py")
        after = root / "src/psychophysics_lab/experiments" / before.name
        for path, key in ((before, "before_sha256_lf"), (after, "after_sha256_lf")):
            raw = path.read_bytes().replace(b"\r\n", b"\n")
            assert hashlib.sha256(raw).hexdigest() == contract[key], (identity, key)
        return before
    return None
