<template>
	<div>
		<div>
			<span class="min-max-inputs">
				<input class="form-control form-input" type="date" v-model="minFilterValue" @change="change" />
				<br />
				<input class="form-control form-input" type="date" v-model="maxFilterValue" @change="change" />
			</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

declare const moment: any

const emit = defineEmits(['update_filters'])
const { values, attribute_name, attribute_id, init_values } = defineProps<{
	values: any[]
	attribute_name: string
	attribute_id: string
	init_values?: string[]
}>()

const minFilterValue = ref(0)
const maxFilterValue = ref(0)

onMounted(() => {
	if (values) {
		const refValues = init_values || values ? Array.from(init_values || values) : []
		minFilterValue.value = moment(refValues[0] * 1000).format('YYYY-MM-DD')
		maxFilterValue.value = moment(refValues[1] * 1000).format('YYYY-MM-DD')
	}
})

const change = () => {
	emit('update_filters', {
		attribute_name,
		attribute_id,
		values: [minFilterValue.value, maxFilterValue.value],
	})
}
</script>

<style scoped>
.min-max-inputs {
	display: flex;
	flex-direction: column;
	white-space: nowrap;
}

.min-max-inputs input {
	width: 17ch;
	text-align: right;
	margin-right: 1ch;
	margin-bottom: 0.5rem;
}

#slider-div {
	display: flex;
	flex-direction: row;
	margin-top: 30px;
}

#slider-div > div {
	margin: 8px;
}

.slider-label {
	position: absolute;
	background-color: #eee;
	padding: 4px;
	font-size: 0.75rem;
}
</style>
