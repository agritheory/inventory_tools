<template>
	<ul class="list-unstyled sidebar-menu faceted-search-box">
		<li class="sidebar-label" v-for="(comp, idx) in searchComponents" :key="idx">
			<component
				:is="comp.component"
				:values="comp.values"
				:attribute_name="comp.attribute_name"
				@update_filters="update_filters($event)"
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
	// components: { AttributeFilter, FacetedSearchNumericRange },
	data(){
		return { searchComponents: [], filterValues: {} }
	},
	mounted(){
		this.loadAttributeFilters()
		this.search = erpnext.ProductSearch
	},
	methods: {
		update_filters(values){
			console.log('update_filters', values)
			this.filterValues[values['attribute_name']] = values['values']
			console.log(this.filterValues)
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
			if(true){ // TODO: change this to test for portal view or != list view
				frappe.xcall('erpnext.e_commerce.api.get_product_filter_data', {
					query_args: { attributes: this.filterValues }
				}).then(r => {
					let view_type = localStorage.getItem("product_view") || "List View";
					if(view_type == 'List View'){
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
				// this is where the filters should be set in the list view 
			}
		}
	}
}
</script>
<style scoped>
.faceted-search-box {
	min-height: 25rem;
}
</style>
