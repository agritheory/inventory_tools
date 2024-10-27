<template>
	<div>
		<div>
			<div class="min-max-inputs">
				<input class="form-control form-input" type="text" v-model="minFilterValue" @change="change" />
				<input class="form-control form-input" type="text" v-model="maxFilterValue" @change="change" />
			</div>
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

const minFilterValue = ref('0')
const maxFilterValue = ref('0')

onMounted(() => {
	if (values) {
		const refValues = init_values || values ? Array.from(init_values || values) : []
		minFilterValue.value = refValues[0]
		maxFilterValue.value = refValues[1]
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
	display: inline;
	white-space: nowrap;
}
.min-max-inputs input {
	display: inline;
	max-width: 10ch;
	margin-right: 1ch;
	text-align: right;
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
