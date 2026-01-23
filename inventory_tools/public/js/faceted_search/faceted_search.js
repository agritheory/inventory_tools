// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { createApp } from 'vue'

import FacetedSearch from './FacetedSearch.vue'
import AttributeFilter from './AttributeFilter.vue'
import FacetedSearchNumericRange from './FacetedSearchNumericRange.vue'
import FacetedSearchDateRange from './FacetedSearchDateRange.vue'
import FacetedSearchColorPicker from './FacetedSearchColorPicker.vue'

frappe.provide('faceted_search')

faceted_search.mount = el => {
	faceted_search.$search = createApp(FacetedSearch, { props: { doctype: 'Item' } })
	faceted_search.$search.component('AttributeFilter', AttributeFilter)
	faceted_search.$search.component('FacetedSearchNumericRange', FacetedSearchNumericRange)
	faceted_search.$search.component('FacetedSearchDateRange', FacetedSearchDateRange)
	faceted_search.$search.component('FacetedSearchColorPicker', FacetedSearchColorPicker)
	faceted_search.$instance = faceted_search.$search.mount(el)
}

function waitForElement(selector) {
	return new Promise(resolve => {
		if (document.querySelector(selector)) {
			return resolve(document.querySelector(selector))
		}
		const observer = new MutationObserver(mutations => {
			if (document.querySelector(selector)) {
				resolve(document.querySelector(selector))
				observer.disconnect()
			}
		})
		observer.observe(document.body, {
			childList: true,
			subtree: true,
		})
	})
}

function mount_listview() {
	if (!faceted_search.$search && $('#faceted-search').length === 0 && $('.filter-section').length > 0) {
		$('.filter-section').prepend('<li id="faceted-search"></li>')
		waitForElement('#faceted-search').then(async el => {
			faceted_search.mount(el)
		})
	}
}

function mount_ecommerce_view(el) {
	faceted_search.mount(el)
}

waitForElement('[data-route]').then(element => {
	const observer = new MutationObserver(() => {
		if (frappe.boot.inventory_tools_settings[Object.keys(frappe.boot.inventory_tools_settings)[0]].show_in_listview) {
			if (cur_list && cur_list.doctype == 'Item') {
				mount_listview()
			}
		}
	})
	const config = { childList: true, subtree: true }
	observer.observe(element, config)
})

waitForElement('.filter-x-button').then(element => {
	if (cur_list && cur_list.filter_area) {
		cur_list.filter_area.filter_x_button.on('click', () => {
			faceted_search.$instance.resetFacets()
		})
	}
})

waitForElement('#product-filters').then(element => {
	frappe.ready(() => {
		frappe
			.xcall(
				'inventory_tools.inventory_tools.doctype.inventory_tools_settings.inventory_tools_settings.faceted_search_enabled'
			)
			.then(r => {
				if (!r.show_on_website) {
					return
				}
				mount_ecommerce_view(element)
				waitForElement('.toggle-container').then(element => {
					let el = $(element)
					el.prepend(
						`<select class="form-control form-input"
						style="width: 20ch; display: inline; margin-left: 1em; float: right;"
					>
					<option>Title A-Z</option>
					<option>Title Z-A</option>
					<option>Item Code A-Z</option>
					<option>Item Code Z-A</option>
					</select>`
					)
					el.on('change', e => {
						faceted_search.$instance.updateFilters({ sort_order: e.target.value })
					})
				})
			})
	})
})
