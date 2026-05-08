# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

"""
Inventory Tools convention for UOM Conversion Factor rows whose numeric ``value`` is
not meant as a universal constant (e.g. pallet vs mass).

This module is for **reports, validators, and suspicion tooling** only. Core ERPNext
``get_uom_conv_factor`` and related resolution still treat matched rows as scalars;
``contextual`` does not change that unless a future core hook exists.
"""

from __future__ import annotations

from typing import Any, Union
from collections.abc import Mapping

from frappe.query_builder import DocType

from pypika.terms import Criterion as PypikaCriterion

FIELD_CONVERSION_BASIS = "it_conversion_basis"
BASIS_FIXED = "fixed"
BASIS_CONTEXTUAL = "contextual"

ConversionFactorLike = Union[Mapping[str, Any], Any]


def get_conversion_basis(doc: ConversionFactorLike) -> str | None:
	"""Return raw ``it_conversion_basis`` or None if absent / blank."""
	if doc is None:
		return None
	raw = conversion_factor_field(doc, FIELD_CONVERSION_BASIS)
	if raw is None:
		return None
	s = str(raw).strip()
	return s or None


def is_contextual_conversion_factor(doc: ConversionFactorLike) -> bool:
	"""True when this row is explicitly marked contextual (strict tooling carve-out)."""
	return get_conversion_basis(doc) == BASIS_CONTEXTUAL


def participates_in_strict_conversion_checks(doc: ConversionFactorLike) -> bool:
	"""
	Whether naive fixed-ratio / ambiguity suspicion should apply.

	Unset and ``fixed`` participate; ``contextual`` does not.
	Any unexpected stored value participates (fail-safe).
	"""
	basis = get_conversion_basis(doc)
	if basis is None:
		return True
	if basis == BASIS_CONTEXTUAL:
		return False
	return True


def qb_uom_conversion_factor_strict_rows(ucf_alias: DocType) -> PypikaCriterion:
	"""
	Filter on a ``frappe.qb.DocType("UOM Conversion Factor")`` alias.

	Matches rows that **should** be evaluated by strict / suspicion tooling
	(i.e. not explicitly contextual). SQL-safe for NULL ``it_conversion_basis``.
	"""
	column = getattr(ucf_alias, FIELD_CONVERSION_BASIS)
	return column.isnull() | (column != BASIS_CONTEXTUAL)


def qb_uom_conversion_factor_contextual_rows(ucf_alias: DocType) -> PypikaCriterion:
	"""Matches rows explicitly marked contextual (informational carve-out / exclusions)."""
	return getattr(ucf_alias, FIELD_CONVERSION_BASIS) == BASIS_CONTEXTUAL


def conversion_factor_field(doc: ConversionFactorLike, fieldname: str):
	if isinstance(doc, Mapping):
		return doc.get(fieldname)
	getter = getattr(doc, "get", None)
	if callable(getter):
		return getter(fieldname)
	return getattr(doc, fieldname, None)
