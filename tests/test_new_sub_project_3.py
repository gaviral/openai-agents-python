import types

import pytest

import new_sub_project_3.main as main
from new_sub_project_3.catalog import Catalog


def test_catalog_tools_empty() -> None:
    _ = Catalog()
    assert main.catalog_tools() == []


def test_manager_simple(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(main, "run_agent", lambda utterance, model: None)
    main.manager("hello world")
