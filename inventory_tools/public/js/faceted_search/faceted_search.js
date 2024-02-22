import FacetedSearch from './FacetedSearch.vue'
import AttributeFilter from './AttributeFilter.vue'
import FacetedSearchNumericRange from './FacetedSearchNumericRange.vue'
import FacetedSearchDateRange from './FacetedSearchDateRange.vue'
import FacetedSearchColorPicker from './FacetedSearchColorPicker.vue'

frappe.provide('faceted_search')

faceted_search.mount = el => {
	// if (faceted_search.$search && faceted_search.$search._isVue) {
	// 	return
	// }
	faceted_search.$search = new window.Vue({
		el: el,
		render: h => h(FacetedSearch, { props: { doctype: 'Item' } }),
		props: { doctype: 'Item' },
	})
	window.Vue.component('AttributeFilter', AttributeFilter)
	window.Vue.component('FacetedSearchNumericRange', FacetedSearchNumericRange)
	window.Vue.component('FacetedSearchDateRange', FacetedSearchDateRange)
	window.Vue.component('FacetedSearchColorPicker', FacetedSearchColorPicker)
	faceted_search.$search.updateSortOrder = sortOrder => {
		console.log('updated sort order')
	}
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

function mount_list_view() {
	if (faceted_search.$search == undefined && !$('#faceted-search').length) {
		$('.filter-section').prepend('<li id="faceted-search"></li>')
		waitForElement('#faceted-search').then(el => {
			faceted_search.mount(el)
		})
	}
}

function mount_ecommerce_view(el) {
	faceted_search.mount(el)
}

waitForElement('[data-route]').then(element => {
	const observer = new MutationObserver(() => {
		mount_list_view()
	})
	const config = { attributes: true, childList: false, characterData: true }
	observer.observe(element, config)
})

waitForElement('#product-filters').then(element => {
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
			faceted_search.$search.$children[0].updateFilters({ sort_order: e.target.value })
		})
	})
})
