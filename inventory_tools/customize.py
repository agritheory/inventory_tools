# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import json
from pathlib import Path

import frappe


def load_customizations():
	customizations_directory = (
		Path().cwd().parent / "apps" / "check_run" / "check_run" / "check_run" / "custom"
	)
	files = list(customizations_directory.glob("**/*.json"))
	for file in files:
		customizations = json.loads(Path(file).read_text())
		for field in customizations.get("custom_fields"):
			if field.get("module") != "Inventory Tools":
				continue
			existing_field = frappe.get_value("Custom Field", field.get("name"))
			custom_field = (
				frappe.get_doc("Custom Field", field.get("name"))
				if existing_field
				else frappe.new_doc("Custom Field")
			)
			field.pop("modified")
			{custom_field.set(key, value) for key, value in field.items()}
			custom_field.flags.ignore_permissions = True
			custom_field.flags.ignore_version = True
			custom_field.save()
		for prop in customizations.get("property_setters"):
			if prop.get("module") != "Inventory Tools":
				continue
			property_setter = frappe.get_doc(
				{
					"name": prop.get("name"),
					"doctype": "Property Setter",
					"doctype_or_field": prop.get("doctype_or_field"),
					"doc_type": prop.get("doc_type"),
					"field_name": prop.get("field_name"),
					"property": prop.get("property"),
					"value": prop.get("value"),
					"property_type": prop.get("property_type"),
				}
			)
			property_setter.flags.ignore_permissions = True
			property_setter.insert()
