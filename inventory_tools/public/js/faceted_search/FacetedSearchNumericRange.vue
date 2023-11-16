<template>
<div>
	<h5> {{ attribute_name }}</h5>
	<div>
		<div class="min-max-inputs">
			<input class="form-input" type="text" v-model="minFilterValue">
			<input class="form-input" type="text" v-model="maxFilterValue">
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
	}
}
</script>
<style scoped>
.min-max-inputs {
	display: inline;
	white-space:nowrap;
}
.min-max-inputs input{
	max-width: 10ch;
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

