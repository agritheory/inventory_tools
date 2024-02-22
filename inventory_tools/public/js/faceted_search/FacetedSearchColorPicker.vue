<template>
	<div>
		<h5>{{ attribute_name }}</h5>
		<div class="colorpicker">
				<div v-for="(attr, idx) in selectedValues" :key="idx" class="color-card"
				@click="selectColor(attr, idx)"
				>
					<div class="color-display" :style="{'background-color': attr.attribute.color }">
						<p :style="{'color': attr.isChecked ? contrast(attr.attribute.color): 'transparent'}">✓</p>
					</div>
					<span> {{ attr.attribute.name }} </span>
				</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'FacetedSearchColorPicker',
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
						return r.isChecked ? r.attribute.name : null
					})
					.filter(r => {
						return r != null
					}),
			})
		},
		selectColor(attr, idx){
			attr.isChecked = !attr.isChecked
			this.change()
		},
		contrast(color) {
			if (
				(['E', 'F'].includes(color.substring(1, 2).toUpperCase()) && ['E', 'F'].includes(color.substring(3, 4).toUpperCase())) ||
				(['E', 'F'].includes(color.substring(3, 4).toUpperCase()) && ['E', 'F'].includes(color.substring(5, 6).toUpperCase())) ||
				(['E', 'F'].includes(color.substring(1, 2).toUpperCase()) && ['E', 'F'].includes(color.substring(5, 6).toUpperCase()))
			) {
				return '	#192734'
			}
			return 'white'
		}
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
<style scoped>
.colorpicker {
	display: flex;
	flex-wrap: wrap;
}
.color-card {
	display: flex;
	flex-direction:column;
	flex:1;
	min-width: 4rem;
	max-width: 4rem;
}
input {
	display: none;
}
.color-display {
	display: flex;
	min-height: .75rem;
	clip-path: circle(40%);
	flex-direction: column;
	justify-content: center;
	text-align: center;
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