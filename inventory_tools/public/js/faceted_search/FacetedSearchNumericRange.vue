<template>
	<div>
		<h5>{{ attribute_name }}</h5>
		<div>
			<div class="min-max-inputs">
				<input class="form-control form-input" type="text" v-model="minFilterValue" @blur="onChange" />
				<input class="form-control form-input" type="text" v-model="maxFilterValue" @blur="onChange" />
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'FacetedSearchNumericRange',
	props: ['values', 'attribute_name'],
	data() {
		return {
			selectedValues: [],
			minFilterValue: 0,
			maxFilterValue: 0,
		}
	},
	mounted() {
		this.minFilterValue = this.values[0]
		this.maxFilterValue = this.values[1]
	},
	methods: {
		onChange() {
			this.$emit('update_filters', {
				attribute_name: this.attribute_name,
				values: [this.minFilterValue, this.maxFilterValue],
			})
		},
	},
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
