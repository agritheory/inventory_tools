import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import frappe
import pytest
from frappe.utils import get_bench_path


@pytest.fixture(scope="module")
def monkeymodule():
	with pytest.MonkeyPatch.context() as mp:
		yield mp


@pytest.fixture(scope="session", autouse=True)
def mock_settings_env_vars():
	with patch.dict(os.environ, {"FRAPPE_STREAM_LOGGING": "True"}):
		yield


@pytest.fixture(scope="session", autouse=True)
def db_instance(mock_settings_env_vars):
	currentsite = "test_site"
	sites = Path(get_bench_path()) / "sites"
	if (sites / "currentsite.txt").is_file():
		currentsite = (sites / "currentsite.txt").read_text()

	frappe.init(site=currentsite, sites_path=sites)
	frappe.connect()
	frappe.db.commit = MagicMock()
	yield frappe.db
