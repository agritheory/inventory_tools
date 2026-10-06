# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt


def after_install():
	from inventory_tools.patches.add_physical_dimension_reference_index import execute

	execute()
