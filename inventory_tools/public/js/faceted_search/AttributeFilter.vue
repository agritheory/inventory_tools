<template>
<div>
	<h5> {{ attribute_name }}</h5>
	<div v-for="(attr, idx) in selectedValues" :key="idx">
		<input type="checkbox" v-model="attr.isChecked"/>
		<span> {{ attr.attribute }}</span>
	</div>
</div>
</template>
<script>
export default {
	name: 'AttributeFilter',
	props: ['values', 'attribute_name'],
	data() {
		return { selectedValues: [] }
	},
	watch: {
		'selectedValues': function (oldValue, newValue) {
			console.log(oldValue, newValue)
		}
	},
	mounted() {
		this.selectedValues = this.values.map(v => { return { attribute: v, isChecked: false}})
	}
}
</script>
