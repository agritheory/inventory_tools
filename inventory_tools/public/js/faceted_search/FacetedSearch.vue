<template>
	<ul class="list-unstyled sidebar-menu faceted-search-box">
		<li class="sidebar-label" v-for="(comp, idx) in searchComponents" :key="idx">
			<component
				:is="comp.component"
				:values="comp.values"
				:attribute_name="comp.attribute_name"
				@update_filters="update_filters($event)"></component>
		</li>
	</ul>
</template>

<script>
// import { getSearchComponents } from './api.js'
frappe.provide('erpnext')

export default {
	name: 'FacetedSearch',
	props: ['doctype'],
	data() {
		return { searchComponents: [], filterValues: {} }
	},
	mounted() {
		this.loadAttributeFilters()
		this.search = erpnext.ProductSearch
	},
	methods: {
		update_filters(values) {
			console.log('update_filters', values)
			this.filterValues[values['attribute_name']] = values['values']
			console.log(this.filterValues)
			// need to debounce here instead of timeout
			setTimeout(() => {
				this.setFilterValues()
			}, 300)
		},

		loadAttributeFilters() {
			frappe
				.call({
					method: 'inventory_tools.inventory_tools.faceted_search.show_faceted_search_components',
					args: { doctype: 'Item', filters: this.filterValues },
					headers: { 'X-Frappe-CSRF-Token': frappe.csrf_token },
				})
				.then(r => {
					this.searchComponents = r.message
					r.message.forEach(attributeFilter => {
						this.filterValues[attributeFilter.attribute_name] = []
					})
				})
		},

		setFilterValues() {
			// TODO: improve check for portal view
			if (erpnext.e_commerce) {
				frappe
					.xcall('erpnext.e_commerce.api.get_product_filter_data', {
						query_args: { attributes: this.filterValues },
					})
					.then(r => {
						const view_type = localStorage.getItem('product_view') || 'List View'
						if (view_type === 'List View') {
							new erpnext.ProductList({
								items: r.items,
								products_section: $('#products-list-area'),
								settings: r.settings,
								preference: view_type,
							})
						} else {
							new erpnext.ProductGrid({
								items: r.items,
								products_section: $('#products-grid-area'),
								settings: r.settings,
								preference: view_type,
							})
						}
					})
			} else {
				const listview = frappe.get_list_view(this.doctype)
				let filters = listview.filter_area.get()

				for (const [key, value] of Object.entries(this.filterValues)) {
					const attribute = this.searchComponents.find(comp => comp.attribute_name === key)
					if (attribute.field) {
						if (Array.isArray(value)) {
							if (value.length > 0) {
								filters.push([this.doctype, attribute.field, 'in', value])
							} else {
								filters = filters.filter(filter => filter[1] !== attribute.field)
							}
						} else {
							// TODO: handle edge-case?
						}
					}

					listview.filter_area.clear(false)
					listview.filter_area.set(filters)
					listview.refresh()
				}
			}
		},
	},
}
</script>

<style scoped>
.faceted-search-box {
	min-height: 25rem;
}
</style>
