<template>
	<div>
		<h5> {{ attribute_name }}</h5>
		<div>
			<div class="min-max-inputs">
				<input class="form-control form-input" type="date" v-model="minFilterValue" @change="change">
				<input class="form-control form-input" type="date" v-model="maxFilterValue" @change="change">
			</div>
		</div>
	</div>
</template>
<script>
export default {
	name: 'FacetedSearchDateRange',
	props: ['values', 'attribute_name', 'attribute_id'],
	data() {
		return {
			minFilterValue: 0,
			maxFilterValue: 0,
		}
	},
	methods: {
		change() {
			this.$emit(
				'update_filters',
				{
					'attribute_name': this.attribute_name,
					'attribute_id': this.attribute_id,
					'values': [this.minFilterValue, this.maxFilterValue]
				})
		}
	},
	mounted() {
		if(this.values){
			this.minFilterValue = this.values[0]
			this.maxFilterValue = this.values[1]
		}
	}
}
</script>
<style scoped>
.min-max-inputs {
	display: inline;
	white-space: nowrap;
}

.min-max-inputs input {

	width: 20ch;
	text-align: right;
}

#slider-div {
	display: flex;
	flex-direction: row;
	margin-top: 30px;
}

#slider-div>div {
	margin: 8px;
}

.slider-label {
	position: absolute;
	background-color: #eee;
	padding: 4px;
	font-size: 0.75rem;
}
</style>

