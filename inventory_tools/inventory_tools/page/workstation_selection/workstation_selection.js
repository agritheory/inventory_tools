// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.pages['workstation-selection'].on_page_load = function (wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Workstation Selection Chart',
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

	let chart_html = `
        <div class="workstation-operations">
            <div class="chart-header">
                <h5>Workstation Alternatives for Work Order: ${work_order}</h5>
                <p class="text-muted">Select alternative workstations for your operations</p>
            </div>
    `

	operations_data.forEach(function (op, index) {
		chart_html += render_operation_tree_for_page(op, index)
	})

	chart_html += '</div>'
	container.html(chart_html)

	setup_page_workstation_handlers(container, work_order)
}

function render_operation_tree_for_page(operation, index) {
	let alternatives_html = ''

	if (operation.alternatives && operation.alternatives.length > 0) {
		alternatives_html = '<div class="alternative-stations">'
		operation.alternatives.forEach(function (alt) {
			alternatives_html += `
                <div class="workstation-node alternative" data-workstation="${alt.workstation}">
                    <div class="node-content">
                        <div class="workstation-info">
                            <strong>${alt.workstation}</strong>
                            <span class="availability-badge ${get_badge_class_for_page(alt.availability)}">${alt.availability}</span>
                        </div>
                        <div class="workstation-details">
                            <small>Next Available: ${alt.next_available ? frappe.datetime.str_to_user(alt.next_available) : 'Now'}</small>
                            <br>
                            <small>Capacity: ${alt.capacity || 1}/hour</small>
                        </div>
                        <button class="btn btn-sm btn-outline-primary use-workstation-btn mt-2"
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
                    <div class="workstation-node primary" data-workstation="${operation.workstation}">
                        <div class="node-content">
                            <div class="workstation-info">
                                <strong>Primary: ${operation.workstation}</strong>
                                <span class="availability-badge ${get_badge_class_for_page(operation.availability)}">${operation.availability}</span>
                            </div>
                            <div class="workstation-details">
                                <small>Next Available: ${operation.next_available ? frappe.datetime.str_to_user(operation.next_available) : 'Now'}</small>
                                <br>
                                <small>Capacity: ${operation.capacity || 1}/hour</small>
                                <br>
                                <small>Planned Start: ${operation.planned_start_time ? frappe.datetime.str_to_user(operation.planned_start_time) : 'Not set'}</small>
                            </div>
                            <button class="btn btn-sm btn-success use-workstation-btn mt-2"
                                    data-workstation="${operation.workstation}"
                                    data-operation="${operation.operation_name || operation.operation}"
                                    data-operation-display="${operation.operation}">
                                Keep Primary
                            </button>
                        </div>
                    </div>

                    ${alternatives_html}
                </div>
            </div>
        </div>
    `
}

function get_badge_class_for_page(availability) {
	switch (availability) {
		case 'available':
			return 'badge-success'
		case 'busy':
			return 'badge-warning'
		case 'unavailable':
			return 'badge-danger'
		default:
			return 'badge-secondary'
	}
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
