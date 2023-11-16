import FacetedSearch from './FacetedSearch.vue'
import AttributeFilter from './AttributeFilter.vue'
import FacetedSearchNumericRange from './FacetedSearchNumericRange.vue'

frappe.provide('faceted_search')

faceted_search.mount = () => {
	if (cur_list && ['Item', 'Website Item', 'BOM'].includes(cur_list.doctype)) {
		// refactor to handle config object
		if (faceted_search.$search) {
			return
		}
		if (faceted_search.$search == undefined && !$('#faceted-search').length) {
			$('.filter-section').prepend('<li id="faceted-search"></li>')
			waitForElement('#faceted-search').then(() => {
				faceted_search.$search = new window.Vue({
					el: '#faceted-search',
					render: h => h(FacetedSearch, { props: {} }),
					props: { doctype: 'Item' },
				})
				window.Vue.component('AttributeFilter', AttributeFilter)
				window.Vue.component('FacetedSearchNumericRange', FacetedSearchNumericRange)
			})
		}
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

waitForElement('[data-route]').then(element => {
	let observer = new MutationObserver(() => {
		faceted_search.mount()
	})
	const config = { attributes: true, childList: false, characterData: true }
	observer.observe(element, config)
})

if (document.querySelector('#product-filters')) {
	faceted_search.$search = new window.Vue({
		el: '#product-filters',
		render: h => h(FacetedSearch, { props: {} }),
	})
}