// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.pages['workstation-selection'].on_page_load = function (wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Alternative Workstations',
		single_column: true,
	})

	let container = $('<div class="workstation-page-container"></div>').appendTo(page.body)

	let filter_wrapper = $(`
        <div class="sticky-work-order-filter"></div>
    `).prependTo(page.body)

	add_sticky_filter_styles()

	// Add Work Order selector using page.add_field
	let work_order_field = page.add_field({
		fieldtype: 'Link',
		fieldname: 'work_order',
		options: 'Work Order',
		label: 'Work Order',
		reqd: 1,
		change: function () {
			let selected_work_order = work_order_field.get_value()
			if (!selected_work_order) {
				container.find('.chart-display-area').empty()
				return
			}

			container
				.find('.chart-display-area')
				.html(`<div class="text-muted p-4"><i class="fa fa-spinner fa-spin"></i> Loading chart...</div>`)

			frappe.call({
				method: 'inventory_tools.inventory_tools.page.workstation_selection.__init__.get_workstation_availability',
				args: { work_order: selected_work_order },
				callback: function (r) {
					if (r.message) {
						render_page_workstation_chart(container.find('.chart-display-area'), r.message, selected_work_order)
					} else {
						container.find('.chart-display-area').html(`
                            <div class="alert alert-info">
                                <i class="fa fa-info-circle"></i>
                                No operations found for this Work Order or backend method not available.
                            </div>
                        `)
					}
				},
				error: function () {
					container.find('.chart-display-area').html(`
                        <div class="alert alert-warning">
                            <i class="fa fa-exclamation-triangle"></i>
                            Error loading data. Please ensure the backend methods are properly installed.
                        </div>
                    `)
				},
			})
		},
	})
	$(work_order_field.$wrapper).appendTo(filter_wrapper)

	// Place chart display area below the field
	$('<div class="chart-display-area"></div>').appendTo(container)

	// Preload if route contains work order
	let work_order_id = frappe.get_route()[1]
	if (work_order_id) {
		work_order_field.set_value(work_order_id)
	}
}

function add_sticky_filter_styles() {
	if (document.getElementById('sticky-work-order-style')) return

	let style = document.createElement('style')
	style.id = 'sticky-work-order-style'
	style.textContent = `
        .sticky-work-order-filter {
            position: sticky;
            top: 60px; /* height of Frappe navbar */
            background: #fff;
            z-index: 100;
            padding: 15px;
            border-bottom: 1px solid #e0e0e0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
    `
	document.head.appendChild(style)
}

function render_page_workstation_chart(container, operations_data, work_order) {
	if (!operations_data || operations_data.length === 0) {
		container.html(`
            <div class="text-center text-muted p-4">
                <i class="fa fa-info-circle fa-2x mb-2"></i>
                <p>No operations found or no alternative workstations configured.</p>
            </div>
        `)
		return
	}

	// Build the chart HTML
	let chart_html = ``

	operations_data.forEach(function (op, index) {
		chart_html += render_operation_tree_for_page(op, index)
	})

	chart_html += '</div>'

	// Render to conta  iner
	container.html(chart_html)

	setup_page_workstation_handlers(container, work_order)
}

function render_operation_tree_for_page(operation, index) {
	// Sort alternatives by next_available
	let sorted_alternatives = (operation.alternatives || []).slice().sort((a, b) => {
		let a_time = a.next_available ? new Date(a.next_available) : new Date(0)
		let b_time = b.next_available ? new Date(b.next_available) : new Date(0)
		return a_time - b_time
	})

	// Determine primary card class and button
	let primary_card_class = 'primary'
	let primary_btn_class = 'btn-primary'

	const earliest_alt_time = sorted_alternatives[0]?.next_available
		? new Date(sorted_alternatives[0].next_available)
		: null
	const primary_time = operation.next_available ? new Date(operation.next_available) : new Date(0)

	// Check if primary is truly the earliest option
	const primary_is_earliest = !earliest_alt_time || primary_time <= earliest_alt_time

	if (!operation.is_bom_default) {
		// Purple - non-default workstation chosen
		primary_card_class += ' non-default'
		primary_btn_class = 'btn-purple'
	} else if (operation.availability === 'available' && primary_is_earliest) {
		// Green - primary is available and earliest
		primary_card_class += ' earliest'
		primary_btn_class = 'btn-success'
	} else if (operation.availability === 'busy' || !primary_is_earliest) {
		// Yellow - primary is busy OR not the earliest option
		primary_card_class += ' busy'
		primary_btn_class = 'btn-warning'
	}

	// Primary card HTML (removed "Primary:")
	let primary_html = `
        <div class="workstation-node ${primary_card_class}" data-workstation="${operation.workstation}">
            <div class="node-content">
                <div class="workstation-info">
                    <strong>${operation.workstation}</strong>
                </div>
                <div class="workstation-details">
                    <div>Next Available: ${operation.next_available ? frappe.datetime.str_to_user(operation.next_available) : 'Now'}</div>
                    <div>Capacity: ${operation.capacity || 1}/hour</div>
                    <div>Planned Start: ${operation.planned_start_time ? frappe.datetime.str_to_user(operation.planned_start_time) : 'Not set'}</div>
                </div>
            </div>
        </div>
    `
	// Alternatives HTML
	let alternatives_html = ''
	if (sorted_alternatives.length > 0) {
		alternatives_html = '<div class="alternative-stations">'
		sorted_alternatives.forEach((alt, i) => {
			let alt_card_class = 'alternative'
			let alt_btn_class = 'btn-outline-primary'

			if (i === 0) {
				alt_card_class += ' earliest' // green
				alt_btn_class = 'btn-success'
			} else {
				alt_card_class += ' busy' // yellow
				alt_btn_class = 'btn-warning'
			}

			alternatives_html += `
                <div class="workstation-node ${alt_card_class}" data-workstation="${alt.workstation}">
                    <div class="node-content">
                        <div class="workstation-info">
                            <strong>${alt.workstation}</strong>
                        </div>
                        <div class="workstation-details">
                            <div>Next Available: ${alt.next_available ? frappe.datetime.str_to_user(alt.next_available) : 'Now'}</div>
                            <div>Capacity: ${alt.capacity || 1}/hour</div>
                        </div>
                        <button class="btn btn-sm ${alt_btn_class} use-workstation-btn mt-2"
                                data-workstation="${alt.workstation}"
                                data-operation="${operation.operation_name || operation.operation}"
                                data-operation-display="${operation.operation}">
                            Use Alternative
                        </button>
                    </div>
                </div>
            `
		})
		alternatives_html += '</div>'
	} else {
		alternatives_html = `
            <div class="no-alternatives">
                <small class="text-muted">No alternative workstations configured for this operation</small>
            </div>
        `
	}

	// Wrap everything in operation tree
	return `
        <div class="operation-tree" data-operation="${operation.operation}">
            <div class="operation-header">
                <h6>
                    <span class="operation-number">${operation.idx}.</span>
                    ${operation.operation}
                </h6>
            </div>
            <div class="workstation-tree">
                <div class="primary-branch">
                    ${primary_html}
                    ${alternatives_html}
                </div>
            </div>
        </div>
    `
}

function setup_page_workstation_handlers(container, work_order) {
	container.find('.use-workstation-btn').click(function () {
		let btn = $(this)
		let workstation = btn.data('workstation')
		let operation = btn.data('operation')
		let operation_display = btn.data('operation-display')

		frappe.confirm(
			__('Are you sure you want to assign workstation "{0}" to operation "{1}"?', [workstation, operation_display]),
			function () {
				// Show loading
				btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Assigning...')

				frappe.call({
					method: 'inventory_tools.inventory_tools.page.workstation_selection.__init__.assign_workstation',
					args: {
						work_order: work_order,
						operation: operation,
						workstation: workstation,
					},
					callback: function (r) {
						if (r.message && r.message.status === 'success') {
							frappe.show_alert({
								message: r.message.message,
								indicator: 'green',
							})

							frappe.call({
								method:
									'inventory_tools.inventory_tools.page.workstation_selection.__init__.get_workstation_availability',
								args: { work_order: work_order },
								callback: function (res) {
									if (res.message) {
										render_page_workstation_chart(container, res.message, work_order)
									}
								},
							})

							// Reload the chart
							container.closest('.workstation-page-container').find('.load-chart-btn').click()
						} else {
							btn.prop('disabled', false).html('Use Alternative')
							frappe.msgprint(__('Failed to assign workstation'))
						}
					},
					error: function () {
						btn.prop('disabled', false).html('Use Alternative')
						frappe.msgprint(__('Error occurred while assigning workstation'))
					},
				})
			},
			function () {
				// User cancelled
			}
		)
	})
}
