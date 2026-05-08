# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import json
from pathlib import Path
from unittest.mock import MagicMock

import frappe
import frappe.utils.redis_queue as redis_queue_module
import pytest
from frappe.utils import get_bench_path

redis_queue_get_connection_original = redis_queue_module.RedisQueue.get_connection


def mock_redis_queue_connection(*args, **kwargs):
	"""Standalone pytest often has no Redis; avoid enqueue-time connection failures."""
	conn = MagicMock()
	conn.ping.return_value = True
	return conn


def get_test_logger(*args, **kwargs):
	from frappe.utils.logger import get_logger

	return get_logger(
		module=None,
		with_more_info=False,
		allow_site=True,
		filter=None,
		max_size=100_000,
		file_count=20,
		stream_only=True,
	)


@pytest.fixture(scope="session", autouse=True)
def db_instance():
	frappe.logger = get_test_logger

	currentsite = "test_site"
	sites = Path(get_bench_path()) / "sites"
	if (sites / "common_site_config.json").is_file():
		currentsite = json.loads((sites / "common_site_config.json").read_text()).get("default_site")

	frappe.init(site=currentsite, sites_path=sites)

	redis_queue_module.RedisQueue.get_connection = classmethod(mock_redis_queue_connection)

	try:
		frappe.connect()
		frappe.db.commit = MagicMock()
		yield frappe.db
	finally:
		redis_queue_module.RedisQueue.get_connection = redis_queue_get_connection_original
