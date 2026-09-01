# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import pytest


@pytest.fixture(scope="module")
def monkeymodule():
	with pytest.MonkeyPatch.context() as mp:
		yield mp
