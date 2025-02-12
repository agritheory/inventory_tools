<template>
	<div v-if="horizontalGrids && verticalGrids" class="grid-container">
		<div class="dimension-display">{{ document.horizontal }}x{{ verticalGrids }} {{ uom }}</div>

		<div
			ref="container"
			class="grid-wrapper"
			@mousedown="startPainting"
			@mousemove="paint"
			@mouseup="stopPainting"
			@mouseleave="stopPainting">
			<img :src="floor_plan" class="background-image" @dragstart.prevent />

			<!-- Grid Overlay with Corrected Offset -->
			<div
				class="grid-overlay"
				:style="{
					backgroundImage: `linear-gradient(90deg, ${gridLines}), linear-gradient(180deg, ${gridLines})`,
					top: `${(offsetValues.top / horizontalGrids) * 100}%`,
					left: `${(offsetValues.left / horizontalGrids) * 100}%`,
					right: `${(offsetValues.right / horizontalGrids) * 100}%`,
					bottom: `${(offsetValues.bottom / horizontalGrids) * 100}%`,
				}" />

			<!-- Walkable Cells with Corrected Offset -->
			<div
				v-for="x in horizontalGrids"
				:key="x"
				class="cell-container"
				:style="{
					top: `${(offsetValues.top / horizontalGrids) * 100}%`,
					left: `${(offsetValues.left / horizontalGrids) * 100}%`,
					right: `${(offsetValues.right / horizontalGrids) * 100}%`,
					bottom: `${(offsetValues.bottom / horizontalGrids) * 100}%`,
				}">
				<div
					v-for="y in verticalGrids"
					:key="`${x - 1},${y - 1}`"
					class="grid-cell"
					:class="{ walkable: isCellWalkable(x - 1, y - 1) }"
					:style="{
						left: `${((x - 1) / horizontalGrids) * 100}%`,
						top: `${((y - 1) / verticalGrids) * 100}%`,
						width: `${100 / horizontalGrids}%`,
						height: `${100 / verticalGrids}%`,
					}" />
			</div>

			<!-- Hover Indicator with Corrected Offset -->
			<div
				class="hover-indicator"
				:style="{
					left: `${(mouseCell.x / horizontalGrids) * 100}%`,
					top: `${(mouseCell.y / verticalGrids) * 100}%`,
					width: `${100 / horizontalGrids}%`,
					height: `${100 / verticalGrids}%`,
					opacity: isHoverValid ? '0.5' : '0',
					transform: `translate(${(offsetValues.left / horizontalGrids) * 100}%, ${
						(offsetValues.top / horizontalGrids) * 100
					}%)`,
				}" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { useElementBounding, useElementSize, useMouseInElement } from '@vueuse/core'
import { computed, onMounted, ref, useTemplateRef } from 'vue'

export type WarehousePlan = {
	floor_plan: string
	uom: string
	horizontal: number
	vertical: number
	offset: string
	matrix?: string
}

const { imageUrl, initialWalkableCells = [] } = defineProps<{
	imageUrl: string
	initialWalkableCells?: { x: number; y: number }[]
}>()

const emit = defineEmits(['update:walkableCells'])

const containerRef = useTemplateRef('container')
const containerRect = useElementBounding(containerRef)

const horizontalGrids = ref(0)
const verticalGrids = ref(0)
const floor_plan = ref()
const uom = ref()
const offsetString = ref('')
const isPainting = ref(false)
const paintMode = ref(false) // true for adding cells, false for removing
const walkableCells = ref(new Set(initialWalkableCells.map(cell => `${cell.x},${cell.y}`)))

const { width, height } = useElementSize(containerRef)
const { elementX, elementY } = useMouseInElement(containerRef)

const offsetValues = computed(() => {
	const defaultOffsets = { top: 0, left: 0, bottom: 0, right: 0 }
	if (!offsetString.value) return defaultOffsets

	const values = offsetString.value.split(',').map(v => parseFloat(v) || 0)
	return {
		top: values[0] || 0,
		left: values[1] || 0,
		bottom: values[2] || 0,
		right: values[3] || 0,
	}
})

const adjustedDimensions = computed(() => {
	const availableWidth =
		width.value * (1 - (offsetValues.value.left + offsetValues.value.right) / horizontalGrids.value)
	const availableHeight =
		height.value * (1 - (offsetValues.value.top + offsetValues.value.bottom) / horizontalGrids.value)
	return { width: availableWidth, height: availableHeight }
})

const cellDimensions = computed(() => ({
	width: adjustedDimensions.value.width / horizontalGrids.value,
	height: adjustedDimensions.value.height / verticalGrids.value,
}))

const mouseCell = computed(() => {
	const adjustedX = elementX.value - (width.value * offsetValues.value.left) / horizontalGrids.value
	const adjustedY = elementY.value - (height.value * offsetValues.value.top) / horizontalGrids.value

	return {
		x: Math.floor(adjustedX / cellDimensions.value.width),
		y: Math.floor(adjustedY / cellDimensions.value.height),
	}
})

const isHoverValid = computed(() => {
	return (
		mouseCell.value.x >= 0 &&
		mouseCell.value.x < horizontalGrids.value &&
		mouseCell.value.y >= 0 &&
		mouseCell.value.y < verticalGrids.value
	)
})

const gridLines = computed(() => {
	const lines: string[] = []
	const dimension = horizontalGrids.value
	for (let i = 1; i < dimension; i++) {
		const percentage = (i / dimension) * 100
		lines.push(`rgba(0,0,0,0.1) ${percentage}%`)
	}
	return lines.join(',')
})

const document = computed(() => {
	const warehousePlan = window.cur_frm.doc as WarehousePlan

	// if (warehousePlan.matrix) {
	// 	walkableCells.value = initializeFromMatrix(warehousePlan.matrix)
	// 	emitUpdate()
	// }

	return {
		image: warehousePlan.floor_plan,
		uom: warehousePlan.uom,
		horizontal: warehousePlan.horizontal,
		vertical: warehousePlan.vertical,
		offset: warehousePlan.offset,
		matrix: warehousePlan.matrix,
	}
})

const watchFrappeFields = () => {
	if (!window.cur_frm) {
		console.warn('Frappe form not found')
		return
	}
	floor_plan.value = window.cur_frm.doc.floor_plan
	uom.value = window.cur_frm.doc.uom
	horizontalGrids.value = window.cur_frm.doc.horizontal || 0
	verticalGrids.value = window.cur_frm.doc.vertical || 0
	offsetString.value = window.cur_frm.doc.offset || '0,0,0,0'
	if (window.cur_frm.doc.matrix) {
		walkableCells.value = initializeFromMatrix(window.cur_frm.doc.matrix) as Set<string>
		emitUpdate()
	}
}

const getCellFromEvent = (event: MouseEvent) => {
	const adjustedX =
		event.clientX - (containerRect.left.value || 0) - (width.value * offsetValues.value.left) / horizontalGrids.value
	const adjustedY =
		event.clientY - (containerRect.top.value || 0) - (height.value * offsetValues.value.top) / horizontalGrids.value

	const x = Math.floor(adjustedX / cellDimensions.value.width)
	const y = Math.floor(adjustedY / cellDimensions.value.height)

	if (x >= 0 && x < horizontalGrids.value && y >= 0 && y < verticalGrids.value) {
		return { x, y }
	}
	return null
}

const startPainting = (event: MouseEvent) => {
	isPainting.value = true
	const cell = getCellFromEvent(event)
	if (cell) {
		paintMode.value = !isCellWalkable(cell.x, cell.y)
		updateCell(cell.x, cell.y)
	}
}

const stopPainting = () => {
	isPainting.value = false
	paintMode.value = false
}

const paint = (event: MouseEvent) => {
	if (!isPainting.value || paintMode.value === null) return

	const cell = getCellFromEvent(event)
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

const emitUpdate = () => {
	const walkableArray = Array.from(walkableCells.value).map(key => {
		const [x, y] = key.split(',').map(Number)
		return { x, y }
	})

	emit('update:walkableCells', walkableArray)
}

const initializeFromMatrix = (matrixString: string) => {
	const cells = new Set<string>()

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

const isCellWalkable = (x: number, y: number) => walkableCells.value.has(`${x},${y}`)

onMounted(() => {
	watchFrappeFields()
})

const getMatrixArray = () => {
	// Create empty matrix filled with zeros
	const matrix = Array(verticalGrids.value)
		.fill(0)
		.map(() => Array(horizontalGrids.value).fill(0))

	// Fill in walkable cells with 1's
	walkableCells.value.forEach(cellKey => {
		const [x, y] = cellKey.split(',').map(Number)
		if (x >= 0 && x < horizontalGrids.value && y >= 0 && y < verticalGrids.value) {
			matrix[y][x] = 1
		}
	})

	return matrix
}

const getMatrixString = () => {
	return JSON.stringify(getMatrixArray())
}

// Optional helper methods:
const getCellValue = (x: number, y: number) => {
	return walkableCells.value.has(`${x},${y}`) ? 1 : 0
}

const getWalkableCellsArray = () => {
	return Array.from(walkableCells.value).map(cell => {
		const [x, y] = cell.split(',').map(Number)
		return { x, y }
	})
}

defineExpose({
	getMatrixArray,
	getMatrixString,
	getCellValue,
	getWalkableCellsArray,
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
