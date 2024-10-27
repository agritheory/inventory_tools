<template>
	<div>
		<div class="colorpicker">
			<div v-for="(attr, idx) in selectedValues" :key="idx" class="color-card" @click="selectColor(attr)">
				<div class="color-display" :style="getBackground(attr)">
					<p :style="{ color: attr.isChecked ? contrast(attr.attribute[1]) : 'transparent' }">✓</p>
				</div>
				<span> {{ attr.attribute[0] }} </span>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

type ColorAttribute = [name: string, color: string, image: string | null | undefined]
type ColorValue = {
	attribute: ColorAttribute
	isChecked: boolean
}

const emit = defineEmits(['update_filters'])
const { values, attribute_name, attribute_id, init_values } = defineProps<{
	values: ColorAttribute[]
	attribute_name: string
	attribute_id: string
	init_values?: string[]
}>()

const selectedValues = ref<ColorValue[]>([])

onMounted(() => {
	if (values?.length > 0) {
		selectedValues.value = values.map(value => {
			const initValues = init_values ? Array.from(init_values) : []
			const isChecked = initValues.includes(value[0])
			return { attribute: value, isChecked }
		})
	}
})

const change = () => {
	emit('update_filters', {
		attribute_name,
		attribute_id,
		values: selectedValues.value
			.map(r => {
				return r.isChecked ? r.attribute[0] : null
			})
			.filter(r => {
				return r != null
			}),
	})
}

const selectColor = (attr: ColorValue) => {
	attr.isChecked = !attr.isChecked
	change()
}

const getBackground = (attr: ColorValue) => {
	const [name, color, image] = attr.attribute
	if (image != undefined) {
		return { 'background-image': `url("${image}")` }
	} else {
		return { 'background-color': color }
	}
}

const contrast = (color: string) => {
	if (
		(['E', 'F'].includes(color.substring(1, 2).toUpperCase()) &&
			['E', 'F'].includes(color.substring(3, 4).toUpperCase())) ||
		(['E', 'F'].includes(color.substring(3, 4).toUpperCase()) &&
			['E', 'F'].includes(color.substring(5, 6).toUpperCase())) ||
		(['E', 'F'].includes(color.substring(1, 2).toUpperCase()) &&
			['E', 'F'].includes(color.substring(5, 6).toUpperCase()))
	) {
		return '#192734'
	} else {
		return 'white'
	}
}
</script>

<style scoped>
.colorpicker {
	display: flex;
	flex-wrap: wrap;
}

.color-card {
	display: flex;
	flex-direction: column;
	flex: 1;
	min-width: 4rem;
	max-width: 4rem;
}

input {
	display: none;
}

.scrollable-filter {
	min-height: 12.5rem;
}

.color-display {
	display: flex;
	min-height: 0.75rem;
	clip-path: circle(40%);
	flex-direction: column;
	justify-content: center;
	text-align: center;
	background-size: contain;
}

.colorpicker span {
	font-size: 90%;
	user-select: none;
	overflow: hidden;
	text-overflow: clip;
	text-align: center;
	align-self: center;
}

.color-display p {
	user-select: none;
	display: relative;
	font-size: 200%;
	margin-bottom: 0.5rem;
	padding-top: 0.125rem;
}
</style>
