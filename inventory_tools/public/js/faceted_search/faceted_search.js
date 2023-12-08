import FacetedSearch from './FacetedSearch.vue'
import AttributeFilter from './AttributeFilter.vue'
import FacetedSearchNumericRange from './FacetedSearchNumericRange.vue'

frappe.provide('faceted_search')

faceted_search.mount = el => {
	// if (faceted_search.$search && faceted_search.$search._isVue) {
	// 	return
	// }
	console.log(el)
	faceted_search.$search = new window.Vue({
		el: el,
		render: h => h(FacetedSearch, { props: { doctype: 'Item' } }),
		props: { doctype: 'Item' },
	})
	window.Vue.component('AttributeFilter', AttributeFilter)
	window.Vue.component('FacetedSearchNumericRange', FacetedSearchNumericRange)
}
// if (faceted_search.$search == undefined) {
// 	await waitForElement('#product-filters').then(el => {
// 		console.log(el)
// 		faceted_search.$search = new window.Vue({
// 			el: el,
// 			render: h => h(FacetedSearch, { props: { doctype: 'Item' }}),
// 		})
// 		window.Vue.component('AttributeFilter', AttributeFilter)
// 		window.Vue.component('FacetedSearchNumericRange', FacetedSearchNumericRange)
// 	})
// }
// if (faceted_search.$search == undefined && window.cur_list && ['Item', 'Website Item', 'BOM'].includes(cur_list.doctype)) {
// 	// refactor to handle config object
// 	if (faceted_search.$search == undefined && !$('#faceted-search').length) {
// 		$('.filter-section').prepend('<li id="faceted-search"></li>')
// 		waitForElement('#faceted-search').then(el => {
// 			faceted_search.$search = new window.Vue({
// 				el: el,
// 				render: h => h(FacetedSearch, { props: { doctype: 'Item' } }),
// 				props: { doctype: 'Item' },
// 			})
// 			window.Vue.component('AttributeFilter', AttributeFilter)
// 			window.Vue.component('FacetedSearchNumericRange', FacetedSearchNumericRange)
// 		})
// 	}
// }
// }

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

function mount_all_products_view(el) {
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
	mount_all_products_view(element)
})
