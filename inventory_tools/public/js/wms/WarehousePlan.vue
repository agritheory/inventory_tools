<template>
	<div v-if="plan.horizontal && plan.vertical" class="grid-container">
		<div class="dimension-display">{{ plan.horizontal }}x{{ plan.vertical }} {{ plan.uom }}</div>

		<div
			ref="container"
			class="grid-wrapper"
			@mousedown="startPainting"
			@mousemove="paint"
			@mouseup="stopPainting"
			@mouseleave="stopPainting">
			<img :src="plan.image" class="background-image" @dragstart.prevent />

			<!-- Grid Overlay with Corrected Offset -->
			<div
				class="grid-overlay"
				:style="{
					backgroundImage: `linear-gradient(90deg, ${gridLines}), linear-gradient(180deg, ${gridLines})`,
					top: `${(offsetGrids.top / plan.vertical) * 100}%`,
					left: `${(offsetGrids.left / plan.horizontal) * 100}%`,
					right: `${(offsetGrids.right / plan.horizontal) * 100}%`,
					bottom: `${(offsetGrids.bottom / plan.vertical) * 100}%`,
				}" />

			<!-- Walkable Cells with Corrected Offset -->
			<div
				v-for="x in plan.horizontal"
				:key="x"
				class="cell-container"
				:style="{
					top: `${(offsetGrids.top / plan.vertical) * 100}%`,
					left: `${(offsetGrids.left / plan.horizontal) * 100}%`,
					right: `${(offsetGrids.right / plan.horizontal) * 100}%`,
					bottom: `${(offsetGrids.bottom / plan.vertical) * 100}%`,
				}">
				<div
					v-for="y in plan.vertical"
					:key="`${x - 1},${y - 1}`"
					class="grid-cell"
					:class="{ walkable: isCellWalkable(x - 1, y - 1) }"
					:style="{
						left: `${((x - 1) / plan.horizontal) * 100}%`,
						top: `${((y - 1) / plan.vertical) * 100}%`,
						width: `${100 / plan.horizontal}%`,
						height: `${100 / plan.vertical}%`,
					}" />

				<!-- Hover Indicator with Corrected Offset -->
				<div
					class="hover-indicator"
					:style="{
						left: `${(hoverCell.x / plan.horizontal) * 100}%`,
						top: `${(hoverCell.y / plan.vertical) * 100}%`,
						width: `${100 / plan.horizontal}%`,
						height: `${100 / plan.vertical}%`,
						opacity: isHoverValid ? '0.5' : '0',
					}" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useElementSize, useMouseInElement } from '@vueuse/core'
import { computed, onMounted, ref, useTemplateRef } from 'vue'

export type WarehousePlan = {
	floor_plan: string
	uom: string
	horizontal: number
	vertical: number
	offset: string
	matrix?: string
}

const emit = defineEmits(['update:walkableCells'])

const containerRef = useTemplateRef('container')
const { width, height } = useElementSize(containerRef)
const { elementX, elementY } = useMouseInElement(containerRef)
const isPainting = ref(false)
const paintMode = ref<boolean | null>(null) // true for adding cells, false for removing
const walkableCells = ref<Set<string>>(new Set())

onMounted(() => {
	// Initialize walkable cells from matrix
	walkableCells.value = initializeFromMatrix(plan.value.matrix)
})

const plan = computed(() => {
	const warehousePlan = window.cur_frm.doc as WarehousePlan
	return {
		image: warehousePlan.floor_plan,
		uom: warehousePlan.uom,
		horizontal: warehousePlan.horizontal || 0,
		vertical: warehousePlan.vertical || 0,
		offset: warehousePlan.offset || '0,0,0,0',
		matrix: warehousePlan.matrix,
	}
})

const offsetGrids = computed(() => {
	const [top, left, bottom, right] = plan.value.offset.split(',').map(v => parseFloat(v) || 0)
	return { top, left, bottom, right }
})

const availableDimensions = computed(() => {
	const widthOffset = offsetGrids.value.left + offsetGrids.value.right
	const heightOffset = offsetGrids.value.top + offsetGrids.value.bottom
	const availableWidth = width.value * (1 - widthOffset / plan.value.horizontal)
	const availableHeight = height.value * (1 - heightOffset / plan.value.vertical)
	return { width: availableWidth, height: availableHeight }
})

const availableCellDimension = computed(() => ({
	width: availableDimensions.value.width / plan.value.horizontal,
	height: availableDimensions.value.height / plan.value.vertical,
}))

const hoverCell = computed(() => {
	const adjustedX = elementX.value - (width.value * offsetGrids.value.left) / plan.value.horizontal
	const adjustedY = elementY.value - (height.value * offsetGrids.value.top) / plan.value.vertical

	return {
		x: Math.floor(adjustedX / availableCellDimension.value.width),
		y: Math.floor(adjustedY / availableCellDimension.value.height),
	}
})

const isHoverValid = computed(() => {
	return (
		hoverCell.value.x >= 0 &&
		hoverCell.value.x < plan.value.horizontal &&
		hoverCell.value.y >= 0 &&
		hoverCell.value.y < plan.value.vertical
	)
})

const gridLines = computed(() => {
	const lines: string[] = []
	for (let i = 1; i < plan.value.horizontal; i++) {
		const percentage = (i / plan.value.horizontal) * 100
		lines.push(`rgba(0,0,0,0.1) ${percentage}%`)
	}
	return lines.join(',')
})

const initializeFromMatrix = (matrixString?: string) => {
	const cells = new Set<string>()
	if (!matrixString) return cells

	try {
		// Parse the string to get the array of arrays
		const matrix: number[][] = JSON.parse(matrixString)

		// Convert matrix 1's to coordinates
		matrix.forEach((row, y) => {
			row.forEach((cell, x) => {
				if (cell === 1) {
					cells.add(`${x},${y}`)
				}
			})
		})

		return cells
	} catch (e) {
		console.warn('Error parsing matrix string:', e)
		return cells
	}
}

const getCellFromEvent = () => {
	const { x, y } = hoverCell.value
	if (isHoverValid.value) return { x, y }
}

const startPainting = () => {
	isPainting.value = true
	const cell = getCellFromEvent()
	if (cell) {
		paintMode.value = !isCellWalkable(cell.x, cell.y)
		updateCell(cell.x, cell.y)
	}
}

const stopPainting = () => {
	isPainting.value = false
	paintMode.value = null
}

const paint = () => {
	if (!isPainting.value || paintMode.value === null) return
	const cell = getCellFromEvent()
	if (cell) {
		updateCell(cell.x, cell.y)
	}
}

const updateCell = (x: number, y: number) => {
	const cellKey = `${x},${y}`
	const currentState = walkableCells.value.has(cellKey)

	if (currentState !== paintMode.value) {
		if (paintMode.value) {
			walkableCells.value.add(cellKey)
		} else {
			walkableCells.value.delete(cellKey)
		}

		emitUpdate()
	}
}

const emitUpdate = () => emit('update:walkableCells', getWalkableCells())

// Helper methods
const getMatrixArray = () => {
	// Create empty matrix filled with zeros
	const matrix = Array(plan.value.vertical)
		.fill(0)
		.map(() => Array(plan.value.horizontal).fill(0))

	// Fill in walkable cells with 1's
	const cells = getWalkableCells()
	for (const { x, y } of cells) {
		if (x >= 0 && x < plan.value.horizontal && y >= 0 && y < plan.value.vertical) {
			matrix[y][x] = 1
		}
	}

	return matrix
}

const isCellWalkable = (x: number, y: number) => walkableCells.value.has(`${x},${y}`)
const getMatrixString = () => JSON.stringify(getMatrixArray())
const getWalkableCells = () =>
	Array.from(walkableCells.value).map(cell => {
		const [x, y] = cell.split(',').map(Number)
		return { x, y }
	})

defineExpose({
	isCellWalkable,
	getMatrixArray,
	getMatrixString,
	getWalkableCells,
})
</script>

<style scoped>
.grid-container {
	position: relative;
}

.dimension-display {
	position: absolute;
	top: 8px;
	right: 8px;
	background-color: rgba(255, 255, 255, 0.8);
	padding: 4px 8px;
	border-radius: 4px;
	font-size: 14px;
	z-index: 1;
}

.grid-wrapper {
	position: relative;
	overflow: hidden;
}

.background-image {
	width: 100%;
	height: 100%;
	object-fit: cover;
}

.grid-overlay {
	position: absolute;
	pointer-events: none;
}

.cell-container {
	position: absolute;
}

.grid-cell {
	position: absolute;
	transition: background-color 0.2s;
}

.grid-cell.walkable {
	background-color: rgba(0, 255, 0, 0.3);
}

.hover-indicator {
	position: absolute;
	border: 2px solid tomato;
	pointer-events: none;
}
</style>
