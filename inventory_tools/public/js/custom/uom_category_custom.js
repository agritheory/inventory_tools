// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('UOM Category', {
	refresh(frm) {
		add_uom_curation_buttons(frm)
		if (frm.is_new() || !frm.doc.name) {
			render_overview_placeholder(frm, __('Save the category first.'))
			return
		}
		if (frm._it_uom_overview_loaded !== frm.doc.name) {
			load_uom_category_overview(frm)
		}
	},
})

function add_uom_curation_buttons(frm) {
	if (!frm.doc.name) {
		return
	}
	const group = __('UOM curation')
	frm.add_custom_button(
		__('Disable unused UOMs in this category'),
		() => disable_unused_uoms_in_this_category(frm),
		group
	)
	frm.add_custom_button(__('Enable all UOMs in this category'), () => enable_uoms_in_this_category(frm), group)
}

function render_overview_placeholder(frm, message) {
	set_overview_html(frm, `<div class="small text-muted">${frappe.utils.escape_html(message || '')}</div>`)
}

function set_overview_html(frm, inner_html) {
	const field = frm.get_field('it_uom_category_overview')
	if (!field || !field.$wrapper) {
		return
	}
	let $dynamic = field.$wrapper.find('.it-uom-dynamic')
	if (!$dynamic.length) {
		field.$wrapper.append('<div class="it-uom-dynamic"></div>')
		$dynamic = field.$wrapper.find('.it-uom-dynamic')
	}
	$dynamic.html(inner_html)
}

function load_uom_category_overview(frm) {
	if (!frm.doc.name) {
		return
	}
	render_overview_placeholder(frm, __('Loading…'))

	const freeze_msg = __('Loading UOM overview…')
	frappe.dom.freeze(freeze_msg)
	frappe
		.xcall('inventory_tools.inventory_tools.overrides.uom_category.get_uom_category_overview', {
			category_name: frm.doc.name,
		})
		.then(message => {
			frm._it_uom_overview_loaded = frm.doc.name
			const rows = message && message.rows ? message.rows : []
			if (!rows.length) {
				render_overview_placeholder(frm, __('No UOM Conversion Factors for this category.'))
				return
			}
			const esc = frappe.utils.escape_html
			const thead = `<tr>
				<th>${esc(__('UOM'))}</th>
				<th>${esc(__('Is UOM Enabled?'))}</th>
				<th>${esc(__('Referenced in other UOM Categories'))}</th>
				<th>${esc(__('Referenced in Item or submitted documents'))}</th>
			</tr>`
			const body = rows
				.map(d => {
					const code = d.uom != null ? String(d.uom) : ''
					const label = d.uom_label != null ? String(d.uom_label) : ''
					const uomCell =
						label && code && label !== code
							? `${esc(label)} <span class="text-muted">(${esc(code)})</span>`
							: esc(label || code)
					return `<tr>
						<td>${uomCell}</td>
						<td>${badge(!!d.uom_enabled)}</td>
						<td>${badge(!!d.ref_other_uom_category)}</td>
						<td>${badge(!!d.in_item_or_submittable)}</td>
					</tr>`
				})
				.join('')
			const table = `
				<p class="text-muted">${esc(
					__(
						'One row per UOM that appears on any conversion factor for this category (as source or target). Other categories: also on a UOM Conversion Factor whose category is not this one. Item/submitted: Link on Item or a line of a submittable DocType. This category’s factors alone do not count toward those two flags.'
					)
				)}</p>
				<table class="table table-bordered table-condensed">
					<thead>${thead}</thead>
					<tbody>${body}</tbody>
				</table>`
			set_overview_html(frm, table)
		})
		.catch(() => {
			frm._it_uom_overview_loaded = null
			render_overview_placeholder(frm, __('Could not load overview.'))
		})
		.finally(() => frappe.dom.unfreeze())
}

function badge(on) {
	return on
		? `<span class="indicator-pill green">${frappe.utils.escape_html(__('Yes'))}</span>`
		: `<span class="indicator-pill red">${frappe.utils.escape_html(__('No'))}</span>`
}

function disable_unused_uoms_in_this_category(frm) {
	if (!frm.doc.name) {
		return
	}
	frappe.confirm(
		__(
			"Disable enabled UOM masters that appear only in this category's conversion factors, are not linked from Item or from lines of submittable documents, and do not appear in conversion factors for other categories? Already-disabled UOMs are skipped."
		),
		() => {
			const freeze_msg = __('Updating UOMs…')
			frappe.dom.freeze(freeze_msg)
			frappe
				.xcall('inventory_tools.inventory_tools.overrides.uom_category.disable_unused_uoms_for_this_category', {
					category_name: frm.doc.name,
				})
				.then(msg => {
					const n = msg && msg.count ? msg.count : 0
					const names = msg && msg.disabled && msg.disabled.length ? msg.disabled.join(', ') : ''
					frappe.show_alert({
						message:
							n > 0
								? `${__('Disabled')}: ${n} — ${frappe.utils.escape_html(names)}`
								: __('No enabled unused UOMs were disabled.'),
						indicator: n > 0 ? 'green' : 'orange',
					})
					load_uom_category_overview(frm)
				})
				.catch(() => frappe.show_alert({ message: __('Could not disable UOMs'), indicator: 'red' }))
				.finally(() => frappe.dom.unfreeze())
		},
		() => {}
	)
}

function enable_uoms_in_this_category(frm) {
	if (!frm.doc.name) {
		return
	}
	frappe.confirm(
		__(
			"Enable UOM masters that meet the same unused definition (this category's factors only, no Item or submittable-line links, no other category's conversion factors) and are disabled on the UOM master?"
		),
		() => {
			const freeze_msg = __('Updating UOMs…')
			frappe.dom.freeze(freeze_msg)
			frappe
				.xcall('inventory_tools.inventory_tools.overrides.uom_category.enable_unused_uoms_for_this_category', {
					category_name: frm.doc.name,
				})
				.then(msg => {
					const n = msg && msg.count ? msg.count : 0
					const names = msg && msg.enabled && msg.enabled.length ? msg.enabled.join(', ') : ''
					frappe.show_alert({
						message:
							n > 0
								? `${__('Enabled')}: ${n} — ${frappe.utils.escape_html(names)}`
								: __('No disabled unused UOMs were enabled.'),
						indicator: n > 0 ? 'green' : 'orange',
					})
					load_uom_category_overview(frm)
				})
				.catch(() => frappe.show_alert({ message: __('Could not enable UOMs'), indicator: 'red' }))
				.finally(() => frappe.dom.unfreeze())
		},
		() => {}
	)
}
