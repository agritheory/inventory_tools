<template>
	<ul class="list-unstyled sidebar-menu faceted-search-box">
		<li class="sidebar-label" v-for="(comp, idx) in searchComponents" :key="idx">
			<component :is="comp.component" :values="comp.values" :attribute_name="comp.attribute_name"></component>
	</li>
</ul>
</template>
<script>
// import { getSearchComponents } from './api.js'

export default {
	name: 'FacetedSearch',
	props: ['doctype'],
	// components: { AttributeFilter, FacetedSearchNumericRange },
	data(){
		return { searchComponents: [] }
	},
	mounted(){
		frappe.xcall('inventory_tools.inventory_tools.faceted_search.show_faceted_search_components', { 'doctype': 'Item' })
		.then(r => {
			this.searchComponents = r
		})
	}
}
</script>
<style scoped>
.faceted-search-box {
	min-height: 25rem;
}
</style>