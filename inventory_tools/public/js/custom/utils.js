// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.provide('frappe.query_report')

// required to add onload triggers to report view
frappe.views.ReportView.prototype.setup_new_doc_event = function () {
	this.$no_result.find('.btn-new-doc').click(() => {
		if (this.settings.primary_action) {
			this.settings.primary_action()
		} else {
			this.make_new_doc()
		}
	})
}

// add onload trigger to report view
frappe.views.ReportView.prototype.setup_view = function () {
	if (this.report_settings && this.settings.onload) {
		this.settings.onload(this)
	}
	this.setup_columns()
	this.setup_new_doc_event() // patched from above
	this.page.main.addClass('report-view')
	this.page.body[0].style.setProperty('--report-filter-height', this.page.page_form.css('height'))
	this.page.body.parent().css('margin-bottom', 'unset')
}

// add 'on report render' event
frappe.views.QueryReport.prototype.hide_loading_screen = function () {
	this.$loading.hide()
	if (this.report_settings && this.report_settings.on_report_render && this.data && this.data.length > 0) {
		this.report_settings.on_report_render(this)
	}
}
