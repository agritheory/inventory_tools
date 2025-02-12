<template>
	<div v-if="gridWidth && gridHeight" class="grid-container">
		<div class="dimension-display">{{ gridWidth }}x{{ gridHeight }} {{ uom }}</div>

		<div
			ref="containerRef"
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
					backgroundImage: `
            linear-gradient(90deg, ${gridLines}),
            linear-gradient(180deg, ${gridLines})
          `,
					top: `${(offsetValues.top / gridWidth) * 100}%`,
					left: `${(offsetValues.left / gridWidth) * 100}%`,
					right: `${(offsetValues.right / gridWidth) * 100}%`,
					bottom: `${(offsetValues.bottom / gridWidth) * 100}%`,
				}" />

			<!-- Walkable Cells with Corrected Offset -->
			<div
				v-for="x in gridWidth"
				:key="x"
				class="cell-container"
				:style="{
					top: `${(offsetValues.top / gridWidth) * 100}%`,
					left: `${(offsetValues.left / gridWidth) * 100}%`,
					right: `${(offsetValues.right / gridWidth) * 100}%`,
					bottom: `${(offsetValues.bottom / gridWidth) * 100}%`,
				}">
				<div
					v-for="y in gridHeight"
					:key="`${x - 1},${y - 1}`"
					class="grid-cell"
					:class="{ walkable: isCellWalkable(x - 1, y - 1) }"
					:style="{
						left: `${((x - 1) / gridWidth) * 100}%`,
						top: `${((y - 1) / gridHeight) * 100}%`,
						width: `${100 / gridWidth}%`,
						height: `${100 / gridHeight}%`,
					}" />
			</div>

			<!-- Hover Indicator with Corrected Offset -->
			<div
				class="hover-indicator"
				:style="{
					left: `${(mouseCell.x / gridWidth) * 100}%`,
					top: `${(mouseCell.y / gridHeight) * 100}%`,
					width: `${100 / gridWidth}%`,
					height: `${100 / gridHeight}%`,
					opacity: isHoverValid ? '0.5' : '0',
					transform: `translate(
            ${(offsetValues.left / gridWidth) * 100}%,
            ${(offsetValues.top / gridWidth) * 100}%
          )`,
				}" />
		</div>
	</div>
</template>

<script setup>
import { ref, computed, defineExpose, defineProps, defineEmits, onMounted } from 'vue'
import { useMouseInElement, useElementSize } from '@vueuse/core'

const props = defineProps({
	imageUrl: {
		type: String,
		required: true,
	},
	initialWalkableCells: {
		type: Array,
		default: () => [],
	},
})

const emit = defineEmits(['update:walkableCells'])

const containerRef = ref(null)
const gridWidth = ref(0)
const gridHeight = ref(0)
const floor_plan = ref()
const uom = ref()
const offsetString = ref('')
const isPainting = ref(false)
const paintMode = ref(null) // true for adding cells, false for removing

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
	const availableWidth = width.value * (1 - (offsetValues.value.left + offsetValues.value.right) / gridWidth.value)
	const availableHeight = height.value * (1 - (offsetValues.value.top + offsetValues.value.bottom) / gridWidth.value)
	return { width: availableWidth, height: availableHeight }
})

const walkableCells = ref(new Set(props.initialWalkableCells.map(cell => `${cell.x},${cell.y}`)))

const cellDimensions = computed(() => ({
	width: adjustedDimensions.value.width / gridWidth.value,
	height: adjustedDimensions.value.height / gridHeight.value,
}))

const mouseCell = computed(() => {
	const adjustedX = elementX.value - (width.value * offsetValues.value.left) / gridWidth.value
	const adjustedY = elementY.value - (height.value * offsetValues.value.top) / gridWidth.value

	return {
		x: Math.floor(adjustedX / cellDimensions.value.width),
		y: Math.floor(adjustedY / cellDimensions.value.height),
	}
})

const isHoverValid = computed(() => {
	return (
		mouseCell.value.x >= 0 &&
		mouseCell.value.x < gridWidth.value &&
		mouseCell.value.y >= 0 &&
		mouseCell.value.y < gridHeight.value
	)
})

const gridLines = computed(() => {
	const lines = []
	const dimension = gridWidth.value
	for (let i = 1; i < dimension; i++) {
		const percentage = (i / dimension) * 100
		lines.push(`rgba(0,0,0,0.1) ${percentage}%`)
	}
	return lines.join(',')
})

const watchFrappeFields = () => {
	if (!window.cur_frm) {
		console.warn('Frappe form not found')
		return
	}
	floor_plan.value = window.cur_frm.doc.floor_plan
	uom.value = window.cur_frm.doc.uom
	gridWidth.value = window.cur_frm.doc.horizontal || 0
	gridHeight.value = window.cur_frm.doc.vertical || 0
	offsetString.value = window.cur_frm.doc.offset || '0,0,0,0'
	if (window.cur_frm.doc.matrix) {
		walkableCells.value = initializeFromMatrix(window.cur_frm.doc.matrix)
		emitUpdate()
	}
}

const getCellFromEvent = event => {
	const rect = containerRef.value.getBoundingClientRect()
	const adjustedX = event.clientX - rect.left - (width.value * offsetValues.value.left) / gridWidth.value
	const adjustedY = event.clientY - rect.top - (height.value * offsetValues.value.top) / gridWidth.value

	const x = Math.floor(adjustedX / cellDimensions.value.width)
	const y = Math.floor(adjustedY / cellDimensions.value.height)

	if (x >= 0 && x < gridWidth.value && y >= 0 && y < gridHeight.value) {
		return { x, y }
	}
	return null
}

const startPainting = event => {
	isPainting.value = true
	const cell = getCellFromEvent(event)
	if (cell) {
		paintMode.value = !isCellWalkable(cell.x, cell.y)
		updateCell(cell.x, cell.y)
	}
}

const stopPainting = () => {
	isPainting.value = false
	paintMode.value = null
}

const paint = event => {
	if (!isPainting.value || paintMode.value === null) return

	const cell = getCellFromEvent(event)
	if (cell) {
		updateCell(cell.x, cell.y)
	}
}

const updateCell = (x, y) => {
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

const initializeFromMatrix = matrixString => {
	try {
		// Parse the string to get the array of arrays
		const matrix = JSON.parse(matrixString)
		const cells = new Set()

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
		return new Set()
	}
}

const isCellWalkable = (x, y) => walkableCells.value.has(`${x},${y}`)

onMounted(() => {
	watchFrappeFields()
})

const getMatrixArray = () => {
	// Create empty matrix filled with zeros
	const matrix = Array(gridHeight.value)
		.fill(0)
		.map(() => Array(gridWidth.value).fill(0))

	// Fill in walkable cells with 1's
	walkableCells.value.forEach(cellKey => {
		const [x, y] = cellKey.split(',').map(Number)
		if (x >= 0 && x < gridWidth.value && y >= 0 && y < gridHeight.value) {
			matrix[y][x] = 1
		}
	})

	return matrix
}

const getMatrixString = () => {
	return JSON.stringify(getMatrixArray())
}

// Optional helper methods:
const getCellValue = (x, y) => {
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
