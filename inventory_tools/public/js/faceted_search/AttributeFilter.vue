<template>
	<div>
		<h5>{{ attribute_name }}</h5>
		<div v-for="(attr, idx) in selectedValues" :key="idx">
			<input type="checkbox" v-model="attr.isChecked" @change="change" />
			<span> {{ attr.attribute }}</span>
		</div>
	</div>
</template>

<script>
export default {
	name: 'AttributeFilter',
	props: ['values', 'attribute_name', 'attribute_id'],
	data() {
		return { selectedValues: [] }
	},
	methods: {
		change() {
			this.$emit('update_filters', {
				attribute_name: this.attribute_name,
				attribute_id: this.attribute_id,
				values: this.selectedValues
					.map(r => {
						return r.isChecked ? r.attribute : null
					})
					.filter(r => {
						return r != null
					}),
			})
		},
	},
	mounted() {
		if (this.values) {
			this.selectedValues = this.values.map(v => {
				return { attribute: v, isChecked: false }
			})
		}
	},
}
</script>
