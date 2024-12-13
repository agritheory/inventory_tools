// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.pages['optimizer'].on_page_load = wrapper => {
	frappe.require(
		[
			'assets/frappe/node_modules/frappe-gantt/dist/frappe-gantt.css',
			'assets/frappe/node_modules/frappe-gantt/dist/frappe-gantt.min.js',
		],
		() => {
			const page = frappe.ui.make_app_page({
				parent: wrapper,
				title: 'Optimizer',
				single_column: true,
			})

			frappe.pages['optimizer'].gantt_view = new OptimizerView(page)
		}
	)
}

class OptimizerView {
	constructor(page) {
		this.page = page
		this.setup_filters()
		this.setup_page()
		this.init_gantt()
	}

	setup_filters() {
		this.page.add_field({
			label: 'Work Order',
			fieldtype: 'Link',
			options: 'Work Order',
			fieldname: 'work_order',
			onchange: () => this.init_gantt(),
		})
		this.page.add_field({
			label: 'Production Item',
			fieldtype: 'Link',
			options: 'Item',
			fieldname: 'production_item',
			onchange: () => this.init_gantt(),
		})
	}

	setup_page() {
		this.list_paging_area = $(`
			<div class="level">
					<div class="level-left">
							<div class="btn-group">
									<button class="btn btn-default btn-sm btn-paging" data-value="Quarter Day">Quarter Day</button>
									<button class="btn btn-default btn-sm btn-paging" data-value="Half Day">Half Day</button>
									<button class="btn btn-default btn-sm btn-paging" data-value="Day">Day</button>
									<button class="btn btn-default btn-sm btn-paging" data-value="Week">Week</button>
									<button class="btn btn-default btn-sm btn-paging" data-value="Month">Month</button>
							</div>
					</div>
			</div>
	 `).appendTo($('.page-form')[0])

		this.setup_paging_events()

		this.container = $('<div class="gantt-container gantt-modern">').appendTo(this.page.main)

		this.output = $('<div class="gantt-view">')
			.css({
				overflow: 'auto',
				minHeight: '200px',
			})
			.appendTo(this.container)[0]

		this.resizer = $('<div class="resizer">')
			.css({
				height: '10px',
				background: '#e0e0e0',
				cursor: 'row-resize',
				margin: '5px 0',
				'&:hover': {
					background: '#bdbdbd',
				},
			})
			.appendTo(this.container)

		this.actual = $('<div class="gantt-view">')
			.css({
				overflow: 'auto',
				minHeight: '200px',
			})
			.appendTo(this.container)[0]

		$(this.container).css({
			display: 'grid',
			'grid-template-rows': '40vh 10px 40vh',
			gap: '0',
			height: '85vh',
		})

		this.setup_resizer()
	}

	init_gantt() {
		const filters = {
			work_order: this.page.fields_dict.work_order.get_value(),
			production_item: this.page.fields_dict.production_item.get_value(),
		}

		frappe
			.xcall('inventory_tools.inventory_tools.page.optimizer.get_work_order_gantt_data', {
				...filters,
			})
			.then(r => {
				this.all_tasks = r
				this.actual_gantt = new Gantt(this.actual, r, {
					view_mode: 'Quarter Day',
					on_click: task => {
						frappe.set_route('Form', 'Work Order', task.id)
					},
				})
				this.output_gantt = new Gantt(this.output, r, {
					view_mode: 'Quarter Day',
					on_click: task => {
						frappe.set_route('Form', 'Work Order', task.id)
					},
					on_date_change: (task, start, end) => {
						this.update_work_order(task.id, start, end)
					},
				})
			})
	}

	update_work_order(name, start, end) {
		frappe.call({
			method: 'frappe.client.set_value',
			args: {
				doctype: 'Work Order',
				name: name,
				fieldname: {
					planned_start_date: start,
					planned_end_date: end,
				},
			},
		})
	}
	setup_resizer() {
		return
		let startY, startHeightTop, startHeightBottom

		this.resizer.on('mousedown', e => {
			startY = e.clientY
			startHeightTop = $(this.output).height()
			startHeightBottom = $(this.actual).height()

			$(document).on('mousemove', mousemove)
			$(document).on('mouseup', mouseup)
		})

		const mousemove = e => {
			const diff = e.clientY - startY
			$(this.output).height(startHeightTop + diff)
			$(this.actual).height(startHeightBottom - diff)
		}

		const mouseup = () => {
			$(document).off('mousemove', mousemove)
			$(document).off('mouseup', mouseup)
		}
	}

	setup_paging_events() {
		this.list_paging_area.find('.btn-paging').click(e => {
			const view_mode = $(e.target).data('value')
			console.log(view_mode)
			this.output_gantt?.change_view_mode(view_mode)
			this.actual_gantt?.change_view_mode(view_mode)
		})
	}
}
