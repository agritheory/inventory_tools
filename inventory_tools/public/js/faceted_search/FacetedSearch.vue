<template>
	<ul class="list-unstyled sidebar-menu faceted-search-box">
		<li v-for="(component, key) in searchComponents" :key="key">
			<div class="faceted-search-attribute" @click="toggleFilters(key)">
				<B> {{ component.attribute_name }} </B>
				<svg class="icon icon-sm float-right">
					<use href="#icon-small-down" v-show="!component.visible"></use>
					<use href="#icon-small-up" v-show="component.visible"></use>
				</svg>
			</div>
			<component
				v-show="component.visible"
				class="scrollable-filter"
				:key="componentKey"
				:is="component.component"
				:attribute_id="component.attribute_id"
				:attribute_name="component.attribute_name"
				:values="component.values"
				:init_values="component.init_values"
				@update_filters="updateFilters" />
			<hr />
		</li>
	</ul>
</template>

<script setup lang="ts">
import { useUrlSearchParams } from '@vueuse/core'
import { computed, onMounted, ref } from 'vue'

export type ListFilters = [string, string, string, any] | [string, string, string, any, boolean] | any[]
export type SearchComponents = { [key: string]: FilterValue }
export type FilterValue = {
	attribute_id: string
	attribute_name: string
	component?: string
	date_values?: boolean
	field?: string
	init_values?: any[]
	numeric_values?: boolean
	sort_order?: string
	values?: any[]
	visible?: boolean
}

frappe.provide('webshop')

const { doctype = 'Item' } = defineProps<{ doctype: string }>()

const params = useUrlSearchParams('history')
const componentKey = ref(0)
const filterValues = ref<{ [key: string]: Partial<FilterValue> }>({})
const searchComponents = ref<SearchComponents>({})
const sortOrder = ref('')

onMounted(async () => {
	await loadFacets()
})

const isFiltered = computed(() => {
	let isFiltered = false
	for (const value of Object.values(filterValues.value)) {
		isFiltered = isFiltered || Boolean(Object.keys(value).length && value.values?.length)
	}
	return isFiltered
})

const toggleFilters = (key: string | number) => {
	searchComponents.value[key].visible = !searchComponents.value[key].visible
}

const resetFacets = async () => {
	filterValues.value = {}
	await loadFacets()
	componentKey.value++
}

const updateFilters = async (values: FilterValue) => {
	if (values.sort_order) {
		sortOrder.value = values.sort_order
	} else {
		filterValues.value[values.attribute_name] = {
			attribute_id: values.attribute_id,
			values: values.values,
		}
	}

	await setFilters()
}

const loadFacets = async () => {
	const { message }: { message: SearchComponents } = await frappe.call({
		method: 'inventory_tools.inventory_tools.faceted_search.show_faceted_search_components',
		args: { doctype, filters: filterValues.value },
		headers: { 'X-Frappe-CSRF-Token': frappe.csrf_token },
	})

	searchComponents.value = message
	for (const [key, value] of Object.entries(message)) {
		filterValues.value[key] = {}
		if (value.attribute_name in params) {
			const paramValue = params[value.attribute_name]
			const values = Array.isArray(paramValue) ? Array.from(paramValue) : [paramValue]
			const searchComponent = searchComponents.value[key]
			searchComponent.init_values = values
			await updateFilters({
				attribute_name: value.attribute_name,
				attribute_id: value.attribute_id,
				values,
			})
		}
	}

	componentKey.value++ // force re-render after applying init values
}

const setFilters = async () => {
	if (!Object.keys(filterValues.value).length) {
		refreshListFilters([])
		return
	}

	if (webshop && window.cur_list === undefined) {
		for (const [key, value] of Object.entries(filterValues.value)) {
			if (value.values) {
				params[key] = value.values
			} else {
				delete params[key]
			}
		}

		const response = await frappe.xcall('webshop.webshop.api.get_product_filter_data', {
			query_args: {
				attributes: filterValues.value,
				sort_order: sortOrder.value,
			},
		})

		if (!response.items) return

		let view_type = localStorage.getItem('product_view') || 'List View'
		if (view_type == 'List View') {
			new webshop.ProductList({
				items: response.items,
				products_section: $('#products-list-area'),
				settings: response.settings,
				preference: view_type,
			})
		} else {
			new webshop.ProductGrid({
				items: response.items,
				products_section: $('#products-grid-area'),
				settings: response.settings,
				preference: view_type,
			})
		}
	} else if (window.cur_list !== undefined) {
		const items = await frappe.xcall('inventory_tools.inventory_tools.faceted_search.get_specification_items', {
			attributes: filterValues.value,
		})
		const listview = frappe.get_list_view(doctype || 'Item')
		let filters: ListFilters = listview.filter_area.get()

		for (const [key, value] of Object.entries(filterValues.value)) {
			const values = value.values
			const attribute = Object.values(searchComponents.value).find(comp => comp.attribute_name === key)

			if (attribute?.field) {
				if (Array.isArray(values)) {
					if (values.length > 0) {
						if (!values[0] && !values[1]) {
							if (!isFiltered.value) {
								refreshListFilters([])
							} else {
								// TODO: handle case where attribute is unchecked
								// TODO: handle case where numeric range is unset
							}
						} else {
							filters.push([doctype, attribute.field, 'in', values])
						}
					} else {
						filters = filters.filter(filter => filter[1] !== attribute.field)
					}

					refreshListFilters(filters)
				} else {
					// TODO: handle edge-case?
				}
			} else {
				if (Array.isArray(values)) {
					if (!values[0] && !values[1]) {
						if (!isFiltered.value) {
							refreshListFilters([])
						} else {
							// TODO: handle case where attribute is unchecked
							// TODO: handle case where numeric range is unset
						}
					} else {
						const existing_name_filter = filters.filter(filter => filter[1] === 'name')
						if (existing_name_filter.length > 0) {
							const existing_name_filter_value = existing_name_filter[3]
							filters = filters.filter(filter => filter[1] !== 'name')
							if (Array.isArray(existing_name_filter_value)) {
								filters.push([doctype, 'name', 'in', [...existing_name_filter_value, ...items]])
							} else {
								filters.push([doctype, 'name', 'in', [existing_name_filter_value, ...items]])
							}
						} else {
							filters.push([doctype, 'name', 'in', items])
						}

						refreshListFilters(filters)
					}
				} else {
					// TODO: handle edge-case?
				}
			}
		}
	}
}

const refreshListFilters = (filters: ListFilters) => {
	const listview = frappe.get_list_view(doctype)
	listview.filter_area.clear(false)
	listview.filter_area.set(filters)
	listview.refresh()
}

defineExpose({ resetFacets, updateFilters })
</script>

<style scoped>
.faceted-search-box {
	min-height: 25rem;
	flex-direction: column;
	flex-basis: 100%;
	flex: 1;
}

.scrollable-filter {
	max-height: 7rem;
	overflow-y: auto;
	margin-bottom: 1rem;
	flex-direction: column;
	flex-wrap: wrap;
	width: 100%;
}

.faceted-search-attribute {
	flex-flow: row;
	cursor: pointer;
}

/* width */
::-webkit-scrollbar {
	width: 11px;
}

/* Track */
::-webkit-scrollbar-track {
	box-shadow: inset 0 0 5px grey;
	border-radius: 7px;
}

/* Handle */
::-webkit-scrollbar-thumb {
	background: var(--gray-700);
	border-radius: 7px;
}

/* Handle on hover */
::-webkit-scrollbar-thumb:hover {
	background: var(--primary);
}

@-moz-document url-prefix() {
	.scrollable-filter {
		scrollbar-width: thin; /* Set the width of the scrollbar */
		scrollbar-color: var(--gray-700) #eee; /* Set the color of the scrollbar thumb and track */
	}
	.scrollable-filter:hover {
		scrollbar-color: var(--primary) #eee;
	}
}
</style>
