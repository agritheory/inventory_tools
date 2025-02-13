<template>
	<div
		id="plant-floor-layout"
		ref="layout"
		:style="{
			'background-image': `url(${frm.doc.plant_floor_layout})`,
			width: '100%',
			// 'height': layoutHeight,
			// 'min-height': layoutHeight,
			'background-position': 'center',
			'background-repeat': 'no-repeat',
			'background-size': 'contain',
		}">
		<canvas style="width: 100%; height: 100%" ref="diagram"></canvas>
	</div>
</template>

<script setup lang="ts">
import { useResizeObserver } from '@vueuse/core'
import { computed, ref, useTemplateRef } from 'vue'

const layoutRef = useTemplateRef('layout')
const diagram = ref(null)

const frm = computed(() => {
	return window.cur_frm
})

const layoutHeight = computed(() => {
	useResizeObserver(layoutRef, entries => {
		const entry = entries[0]
		const dimensions = entry.contentRect
		return `${dimensions.width * 0.78}px`
	})
})
</script>
