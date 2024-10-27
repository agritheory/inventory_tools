<template>
	<div>
		<div v-for="(attr, idx) in selectedValues" :key="idx">
			<input type="checkbox" v-model="attr.isChecked" @change="change" />
			<span>{{ attr.attribute }}</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

const emit = defineEmits(['update_filters'])
const { values, attribute_name, attribute_id, init_values } = defineProps<{
	values: string[]
	attribute_name: string
	attribute_id: string
	init_values?: string[]
}>()

const selectedValues = ref<{ attribute?: string; isChecked?: boolean }[]>([])

onMounted(() => {
	if (values?.length > 0) {
		selectedValues.value = values.map(value => {
			const initValues = init_values ? Array.from(init_values) : []
			const isChecked = initValues.includes(value)
			return { attribute: value, isChecked }
		})
	}
})

const change = () => {
	emit('update_filters', {
		attribute_name,
		attribute_id,
		values: selectedValues.value.map(r => (r.isChecked ? r.attribute : null)).filter(r => r !== null),
	})
}
</script>
