<template>
	<div
		id="plant-floor-layout"
		ref="plant_floor_layout"
		:style="{
			'background-image': `url(${frm.doc.plant_floor_layout})`,
			width: '100%',
			// 'height': plant_floor_layout_height,
			// 'min-height': plant_floor_layout_height,
			'background-position': 'center',
			'background-repeat': 'no-repeat',
			'background-size': 'contain',
		}">
		<canvas style="width: 100%; height: 100%" ref="diagram"></canvas>
	</div>
</template>
<script setup>
import { computed, onMounted, ref, markRaw, watch, unref } from 'vue'
import { useElementSize, useResizeObserver } from '@vueuse/core'

let plant_floor_layout = ref(null)
let diagram = ref(null)

let frm = computed(() => {
	return window.cur_frm
})

let plant_floor_layout_height = computed(() => {
	useResizeObserver(plant_floor_layout, entries => {
		const entry = entries[0]
		const dimensions = entry.contentRect
		return `${dimensions.width.value * 0.78}px`
	})
})
</script>
<style scoped></style>
