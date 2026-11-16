"""Code stays in Git while runtime artifacts can live on Drive."""
import importlib.util
from pathlib import Path

import pytest


def test_separate_artifact_root(monkeypatch, tmp_path):
    source = Path(__file__).resolve().parents[1] / 'src/fpw/paths.py'
    monkeypatch.setenv('FPW_ARTIFACT_ROOT', str(tmp_path))
    spec = importlib.util.spec_from_file_location('isolated_paths', source)
    paths = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(paths)
    assert paths.ROOT == tmp_path.resolve()
    assert paths.CONFIG_YAML == source.parents[2] / 'config.yaml'
    assert paths.LEDGER == tmp_path / 'state/stages.json'
    assert paths.RAW == tmp_path / 'data/raw/project'


def test_default_storage_is_local_checkout(monkeypatch):
    source = Path(__file__).resolve().parents[1] / 'src/fpw/paths.py'
    monkeypatch.delenv('FPW_ARTIFACT_ROOT', raising=False)
    spec = importlib.util.spec_from_file_location('default_paths', source)
    paths = importlib.util.module_from_spec(spec)
    if Path('/content/drive').is_dir():          # on Colab the artifact root is mandatory (guard in paths.py)
        with pytest.raises(RuntimeError, match='FPW_ARTIFACT_ROOT'):
            spec.loader.exec_module(paths)
        return
    spec.loader.exec_module(paths)
    assert paths.ROOT == paths.CODE_ROOT == source.parents[2]
