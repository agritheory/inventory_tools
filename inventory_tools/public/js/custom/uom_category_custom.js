// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('UOM Category', {
	setup(frm) {
		frappe.realtime.on('uom_curation_progress', data => {
			show_uom_curation_progress(frm, data)
		})
	},
	refresh(frm) {
		add_uom_curation_buttons(frm)
		if (frm.is_new() || !frm.doc.name) {
			render_overview_placeholder(frm, __('Save the category first.'))
			return
		}
		if (frm._it_uom_scan_running) {
			return
		}
		load_cached_uom_category_overview(frm).then(has_cache => {
			if (!has_cache && frm._it_uom_overview_loaded !== frm.doc.name) {
				start_uom_usage_scan(frm)
			}
		})
	},
})

function add_uom_curation_buttons(frm) {
	if (!frm.doc.name) {
		return
	}
	const group = __('UOM curation')
	frm.add_custom_button(__('Refresh usage scan'), () => start_uom_usage_scan(frm), group)
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

function render_uom_category_overview(frm, message) {
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
		<th>${esc(__('Transactional usage count'))}</th>
	</tr>`
	const body = rows
		.map(d => {
			const code = d.uom != null ? String(d.uom) : ''
			const label = d.uom_label != null ? String(d.uom_label) : ''
			const uomCell =
				label && code && label !== code
					? `${esc(label)} <span class="text-muted">(${esc(code)})</span>`
					: esc(label || code)
			const usageCount = d.transactional_usage_count != null ? Number(d.transactional_usage_count) : 0
			return `<tr>
				<td>${uomCell}</td>
				<td>${badge(!!d.uom_enabled)}</td>
				<td>${badge(!!d.ref_other_uom_category)}</td>
				<td>${esc(String(usageCount))}</td>
			</tr>`
		})
		.join('')
	const scannedAt =
		message && message.scanned_at
			? `<p class="small text-muted">${esc(__('Last scanned'))}: ${esc(message.scanned_at)}</p>`
			: ''
	const table = `
		<p class="text-muted">${esc(
			__(
				'One row per UOM that appears on any conversion factor for this category (as source or target). Other categories: also on a UOM Conversion Factor whose category is not this one. Transactional usage: total Link-to-UOM references on Item or lines of submittable documents (all UOM link fields). This category’s factors alone do not count toward those flags.'
			)
		)}</p>
		${scannedAt}
		<table class="table table-bordered table-condensed">
			<thead>${thead}</thead>
			<tbody>${body}</tbody>
		</table>`
	set_overview_html(frm, table)
}

function load_cached_uom_category_overview(frm) {
	if (!frm.doc.name) {
		return Promise.resolve(false)
	}
	return frappe
		.xcall('inventory_tools.inventory_tools.overrides.uom_category.get_cached_uom_category_overview', {
			category_name: frm.doc.name,
		})
		.then(message => {
			const rows = message && message.rows ? message.rows : []
			if (!rows.length) {
				render_overview_placeholder(frm, __('No cached usage scan. Starting usage scan…'))
				return false
			}
			frm._it_uom_overview_loaded = frm.doc.name
			render_uom_category_overview(frm, message)
			return true
		})
		.catch(() => {
			render_overview_placeholder(frm, __('Could not load cached overview.'))
			return false
		})
}

function invalidate_uom_category_overview_cache(frm) {
	frm._it_uom_overview_loaded = null
}

function start_uom_usage_scan(frm) {
	if (!frm.doc.name || frm._it_uom_scan_running) {
		return
	}
	invalidate_uom_category_overview_cache(frm)
	frm._it_uom_scan_running = true
	render_overview_placeholder(frm, __('Scanning UOM usage…'))
	frm
		.call('start_uom_usage_scan')
		.then(() => {
			frappe.show_alert({ message: __('Usage scan queued.'), indicator: 'blue' })
		})
		.catch(() => {
			frm._it_uom_scan_running = false
			frappe.show_alert({ message: __('Could not start usage scan.'), indicator: 'red' })
		})
}

function show_uom_curation_progress(frm, data) {
	if (!data || data.category !== frm.doc.name) {
		return
	}

	const phaseLabels = {
		scan: __('Scanning'),
		disable: __('Disabling unused UOMs'),
		enable: __('Enabling unused UOMs'),
	}
	const action = phaseLabels[data.phase] || __('Working')

	if (data.complete) {
		frm._it_uom_scan_running = false
		if (data.rows) {
			frm._it_uom_overview_loaded = frm.doc.name
			render_uom_category_overview(frm, {
				rows: data.rows,
				category: data.category,
				scanned_at: frappe.datetime.now_datetime(),
			})
		}
		if (data.phase === 'disable') {
			const n = data.count || 0
			const names = data.disabled && data.disabled.length ? data.disabled.join(', ') : ''
			frappe.show_alert({
				message:
					n > 0
						? `${__('Disabled')}: ${n} — ${frappe.utils.escape_html(names)}`
						: __('No enabled unused UOMs were disabled.'),
				indicator: n > 0 ? 'green' : 'orange',
			})
		}
		if (data.phase === 'enable') {
			const n = data.count || 0
			const names = data.enabled && data.enabled.length ? data.enabled.join(', ') : ''
			frappe.show_alert({
				message:
					n > 0
						? `${__('Enabled')}: ${n} — ${frappe.utils.escape_html(names)}`
						: __('No disabled unused UOMs were enabled.'),
				indicator: n > 0 ? 'green' : 'orange',
			})
		}
		setTimeout(() => frm.dashboard.hide(), 2000)
		return
	}

	if (!data.total) {
		return
	}

	frm._it_uom_scan_running = true
	let percent = Math.floor((data.current * 100) / data.total)
	let seconds = Math.floor(data.eta)
	let minutes = Math.floor(data.eta / 60)
	let eta_message =
		seconds < 60
			? __('About {0} seconds remaining', [seconds])
			: minutes === 1
			  ? __('About {0} minute remaining', [minutes])
			  : __('About {0} minutes remaining', [minutes])
	let message = __('{0} {1} of {2}, {3}', [action, data.current, data.total, eta_message])
	frm.dashboard.show_progress(__('{0} Progress', [action]), percent, message)
}

function badge(on) {
	return on
		? `<span class="indicator-pill green">${frappe.utils.escape_html(__('Yes'))}</span>`
		: `<span class="indicator-pill red">${frappe.utils.escape_html(__('No'))}</span>`
}

function disable_unused_uoms_in_this_category(frm) {
	if (!frm.doc.name || frm._it_uom_scan_running) {
		return
	}
	frappe.confirm(
		__(
			"Disable enabled UOM masters that appear only in this category's conversion factors, have zero transactional usage, and do not appear in conversion factors for other categories? Already-disabled UOMs are skipped."
		),
		() => {
			invalidate_uom_category_overview_cache(frm)
			frm._it_uom_scan_running = true
			render_overview_placeholder(frm, __('Scanning before disable…'))
			frm
				.call('start_disable_unused_uoms')
				.then(() => {
					frappe.show_alert({ message: __('Disable queued.'), indicator: 'blue' })
				})
				.catch(() => {
					frm._it_uom_scan_running = false
					frappe.show_alert({ message: __('Could not start disable.'), indicator: 'red' })
				})
		},
		() => {}
	)
}

function enable_uoms_in_this_category(frm) {
	if (!frm.doc.name || frm._it_uom_scan_running) {
		return
	}
	frappe.confirm(
		__(
			"Enable UOM masters that meet the same unused definition (this category's factors only, zero transactional usage, no other category's conversion factors) and are disabled on the UOM master?"
		),
		() => {
			invalidate_uom_category_overview_cache(frm)
			frm._it_uom_scan_running = true
			render_overview_placeholder(frm, __('Scanning before enable…'))
			frm
				.call('start_enable_unused_uoms')
				.then(() => {
					frappe.show_alert({ message: __('Enable queued.'), indicator: 'blue' })
				})
				.catch(() => {
					frm._it_uom_scan_running = false
					frappe.show_alert({ message: __('Could not start enable.'), indicator: 'red' })
				})
		},
		() => {}
	)
}
