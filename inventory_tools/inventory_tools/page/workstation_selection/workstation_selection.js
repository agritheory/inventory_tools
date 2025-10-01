// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.pages['workstation-selection'].on_page_load = function (wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Workstation Selection Chart',
		single_column: true,
	})

	let container = $('<div class="workstation-page-container"></div>').appendTo(page.body)

	// Add work order selector using frappe controls
	let filter_section = $(`
        <div class="page-filter-section" style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div class="row">
                <div class="col-md-6">
                    <div class="work-order-field"></div>
                </div>
                <div class="col-md-6">
                    <div class="form-group" style="margin-top: 23px;">
                        <button class="btn btn-primary btn-block load-chart-btn">
                            <i class="fa fa-search"></i> Load Workstation Chart
                        </button>
                    </div>
                </div>
            </div>
        </div>
        <div class="chart-display-area"></div>
    `).appendTo(container)

	// Create work order link field using frappe controls
	let work_order_field = frappe.ui.form.make_control({
		parent: filter_section.find('.work-order-field'),
		df: {
			fieldtype: 'Link',
			options: 'Work Order',
			label: 'Work Order',
			reqd: 1,
			filters: {
				docstatus: 1,
				status: ['not in', ['Completed', 'Cancelled']],
			},
		},
		render_input: true,
	})

	let work_order_id = frappe.get_route()[1] // first arg after page name
	if (work_order_id) {
		work_order_field.set_value(work_order_id)
	}

	// Load chart button handler
	container.find('.load-chart-btn').click(function () {
		let selected_work_order = work_order_field.get_value()

		if (!selected_work_order) {
			frappe.msgprint(__('Please select a Work Order'))
			work_order_field.set_focus()
			return
		}

		let btn = $(this)
		btn.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i> Loading...')

		frappe.call({
			method: 'inventory_tools.inventory_tools.page.workstation_selection.__init__.get_workstation_availability',
			args: {
				work_order: selected_work_order,
			},
			callback: function (r) {
				btn.prop('disabled', false).html('<i class="fa fa-search"></i> Load Workstation Chart')

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
				btn.prop('disabled', false).html('<i class="fa fa-search"></i> Load Workstation Chart')
				container.find('.chart-display-area').html(`
                    <div class="alert alert-warning">
                        <i class="fa fa-exclamation-triangle"></i>
                        Error loading data. Please ensure the backend methods are properly installed.
                    </div>
                `)
			},
		})
	})
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

	// Add styles if not already added
	add_page_chart_styles()

	// Setup click handlers
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

function add_page_chart_styles() {
	if (document.getElementById('page-workstation-chart-styles')) return

	let style = document.createElement('style')
	style.id = 'page-workstation-chart-styles'
	style.textContent = `
        .workstation-page-container {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        }

        .chart-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
            margin-bottom: 20px;
        }

        .operation-tree {
            margin-bottom: 30px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
            overflow: hidden;
        }

        .operation-header {
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 2px solid #e9ecef;
        }

        .operation-number {
            display: inline-block;
            background: #007bff;
            color: white;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            text-align: center;
            line-height: 24px;
            font-size: 12px;
            margin-right: 10px;
        }

        .workstation-tree {
            padding: 20px;
        }

        .primary-branch {
            display: flex;
            gap: 20px;
            align-items: flex-start;
        }

        .workstation-node {
            border: 2px solid #e9ecef;
            border-radius: 12px;
            background: white;
            transition: all 0.3s ease;
            min-width: 280px;
        }

        .workstation-node.primary {
            border-color: #28a745;
            background: linear-gradient(135deg, #f8fff9 0%, #e8f5e8 100%);
        }

        .workstation-node.alternative {
            border-color: #17a2b8;
            background: linear-gradient(135deg, #f0fcff 0%, #e0f7ff 100%);
        }

        .node-content {
            padding: 20px;
        }

        .workstation-info {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .availability-badge {
            padding: 4px 8px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            color: white;
        }

        .badge-success { background: #28a745; }
        .badge-warning { background: #ffc107; color: #212529; }
        .badge-danger { background: #dc3545; }

        .workstation-details {
            margin-bottom: 15px;
            color: #6c757d;
            font-size: 13px;
        }

        .alternative-stations {
            display: flex;
            flex-direction: column;
            gap: 15px;
            flex: 1;
        }

        .no-alternatives {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px 20px;
            background: #f8f9fa;
            border: 2px dashed #dee2e6;
            border-radius: 12px;
            text-align: center;
        }

        .use-workstation-btn {
            width: 100%;
            font-weight: 600;
        }

        @media (max-width: 768px) {
            .primary-branch { flex-direction: column; }
            .workstation-node { min-width: auto; width: 100%; }
        }
    `
	document.head.appendChild(style)
}
