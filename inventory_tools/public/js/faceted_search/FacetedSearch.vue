<template>
	<ul class="list-unstyled sidebar-menu faceted-search-box">
		<li class="sidebar-label" v-for="(comp, idx) in searchComponents" :key="idx">
			<component
				:is="comp.component"
				:values="comp.values"
				:attribute_id="comp.attribute_id"
				:attribute_name="comp.attribute_name"
				@update_filters="updateFilters($event)"
			></component>
	</li>
</ul>
</template>
<script>
// import { getSearchComponents } from './api.js'
frappe.provide('erpnext')

export default {
	name: 'FacetedSearch',
	props: ['doctype'],
	data(){
		return { searchComponents: [], filterValues: {}, sortOrder: '' }
	},
	mounted(){
		frappe.ready(() => {
			this.loadAttributeFilters()
		})
	},
	methods: {
		updateFilters(values){
			if('sort_order' in values){
				this.sortOrder = values
			} else {
				this.filterValues[values.attribute_name] = { attribute_id: values.attribute_id, values: values.values}
			}
			// need to debounce here instead of timeout
			setTimeout(() => {
				this.setFilterValues()
			}, 300)
		},
		loadAttributeFilters(){
			frappe.call({
				method: 'inventory_tools.inventory_tools.faceted_search.show_faceted_search_components',
				args: { 'doctype': 'Item', 'filters': this.filterValues },
				headers: { 'X-Frappe-CSRF-Token': frappe.csrf_token },
			},
			).then(r => {
				this.searchComponents = r.message
				r.message.forEach(attributeFilter => {
					this.filterValues[attributeFilter.attribute_name] = []
				})
			})
		},
		setFilterValues(){
			if(erpnext.e_commerce){
				frappe.xcall('erpnext.e_commerce.api.get_product_filter_data', {
					query_args: { attributes: this.filterValues, sort_order: this.sortOrder }
				}).then(r => {
					let view_type = localStorage.getItem("product_view") || "List View";
					if(!r.items){
						return
					} else if(view_type == 'List View'){
						new erpnext.ProductList({
							items: r.items,
							products_section: $("#products-list-area"),
							settings: r.settings,
							preference: view_type
						})
					} else {
						new erpnext.ProductGrid({
							items: r.items,
							products_section: $("#products-grid-area"),
							settings: r.settings,
							preference: view_type
						})
					}
				})
			} else {
				const listview = frappe.get_list_view(this.doctype)
				let filters = listview.filter_area.get()

				for (const [key, value] of Object.entries(this.filterValues)) {
					const values = value.values
					const attribute = this.searchComponents.find(comp => comp.attribute_name === key)

					if (attribute.field) {
						if (Array.isArray(values)) {
							if (values.length > 0) {
								if (!values[0] && !values[1]) {
									// TODO: handle case where numeric range is unset
								} else {
									filters.push([this.doctype, attribute.field, 'in', values])
								}
							} else {
								filters = filters.filter(filter => filter[1] !== attribute.field)
							}

							this.refreshFilters(filters)
						} else {
							// TODO: handle edge-case?
						}
					} else {
						if (Array.isArray(values)) {
							if (!values[0] && !values[1]) {
								// TODO: handle case where numeric range is unset
							} else {
								frappe
									.xcall('inventory_tools.inventory_tools.faceted_search.get_specification_items', {
										doctype: this.doctype,
										attributes: this.filterValues,
									})
									.then(items => {
										const existing_name_filter = filters.filter(filter => filter[1] === 'name')
										if (existing_name_filter.length > 0) {
											const existing_name_filter_value = existing_name_filter[3]
											filters = filters.filter(filter => filter[1] !== 'name')
											if (Array.isArray(existing_name_filter_value)) {
												filters.push([this.doctype, 'name', 'in', [...existing_name_filter_value, ...items]])
											} else {
												filters.push([this.doctype, 'name', 'in', [existing_name_filter_value, ...items]])
											}
										} else {
											filters.push([this.doctype, 'name', 'in', items])
										}

										this.refreshFilters(filters)
									})
							}
						} else {
							// TODO: handle edge-case?
						}
					}
				}
			}
		},
		refreshFilters(filters) {
			const listview = frappe.get_list_view(this.doctype)
			listview.filter_area.clear(false)
			listview.filter_area.set(filters)
			listview.refresh()
		},
	}
}
</script>
<style scoped>
.faceted-search-box {
	min-height: 25rem;
}
</style>
