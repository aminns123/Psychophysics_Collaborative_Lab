"""Maintainer builder fails closed before allocating or replacing a package."""
import hashlib
from pathlib import Path

import pytest
from scripts import build_windows_candidate as builder


def test_cached_artifact_is_hash_checked_without_network(tmp_path, monkeypatch):
    path = tmp_path / 'approved.bin'; path.write_bytes(b'approved')
    record = dict(filename=path.name, sha256=hashlib.sha256(b'approved').hexdigest())
    monkeypatch.setattr(builder.urllib.request, 'urlretrieve', lambda *_: pytest.fail('unexpected network'))
    assert builder.artifact(record, tmp_path, False) == path
    path.write_bytes(b'changed')
    with pytest.raises(ValueError, match='altered'): builder.artifact(record, tmp_path, False)


def test_missing_artifact_requires_deliberate_maintainer_download(tmp_path):
    with pytest.raises(ValueError, match='Missing reviewed artifact'):
        builder.artifact(dict(filename='missing.bin',sha256='0'*64),tmp_path,False)
    assert not list(tmp_path.iterdir())


def test_wrong_download_never_becomes_approved_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(builder.urllib.request, 'urlretrieve', lambda _, dest: Path(dest).write_bytes(b'wrong'))
    with pytest.raises(ValueError, match='hash mismatch'):
        builder.artifact(dict(filename='approved.bin',sha256='0'*64,url='https://example.invalid'),tmp_path,True)
    assert not (tmp_path/'approved.bin').exists()


def test_builder_never_overwrites_or_builds_inside_source(tmp_path):
    old=tmp_path/'old';old.mkdir();(old/'identity').write_bytes(b'preserve')
    with pytest.raises(ValueError,match='never overwritten'): builder.build(old,tmp_path/'cache','candidate')
    assert (old/'identity').read_bytes()==b'preserve'
    with pytest.raises(ValueError,match='separate'): builder.build(builder.ROOT/'candidate-test-output',tmp_path/'cache','candidate')
