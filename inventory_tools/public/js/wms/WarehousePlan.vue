<template>
	<div v-if="plan.horizontal && plan.vertical">
		<div class="toolbar">
			<button v-if="walkableRef" @click="toggleWalkable" class="btn btn-primary toolbar-walkable">
				Toggle Walkable
			</button>
			<button v-if="gridRef" @click="toggleGrid" class="btn btn-primary toolbar-grid">Toggle Grid</button>
		</div>

		<div class="overlay">
			<div class="overlay-dimension">{{ plan.horizontal }}x{{ plan.vertical }} {{ plan.uom }}</div>
		</div>

		<div ref="container" class="container">
			<konva-stage
				ref="stage"
				:config="stageConfig"
				@mousedown="startPainting"
				@mousemove="paint"
				@mouseup="stopPainting"
				@mouseleave="stopPainting">
				<!-- Background Image Layer -->
				<konva-layer ref="image">
					<konva-image :config="imageConfig" />
				</konva-layer>

				<!-- Grid Lines Layer -->
				<konva-layer ref="grid">
					<konva-rect :config="gridConfig" />

					<!-- Vertical Grid Lines -->
					<konva-line
						v-for="index in plan.horizontal - 1"
						:key="`v-${index}`"
						:config="getHorizontalGridConfig(index)" />

					<!-- Horizontal Grid Lines -->
					<konva-line v-for="index in plan.vertical - 1" :key="`h-${index}`" :config="getVerticalGridConfig(index)" />
				</konva-layer>

				<!-- Walkable Cells Layer -->
				<konva-layer ref="walkable">
					<konva-rect
						v-for="cell in walkableCellsArray"
						:key="`cell-${cell.x}-${cell.y}`"
						:config="getWalkableCellConfig(cell.x, cell.y)" />
				</konva-layer>

				<!-- Hover Indicator Layer -->
				<konva-layer ref="hover">
					<konva-rect :config="hoverConfig" />
				</konva-layer>
			</konva-stage>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useElementSize } from '@vueuse/core'
import type { Layer } from 'konva/lib/Layer'
import type { KonvaEventObject } from 'konva/lib/Node'
import type { ImageConfig } from 'konva/lib/shapes/Image'
import type { LineConfig } from 'konva/lib/shapes/Line'
import type { RectConfig } from 'konva/lib/shapes/Rect'
import { Stage, type StageConfig } from 'konva/lib/Stage'
import { ref, computed, onMounted, watch, useTemplateRef, type ShallowRef } from 'vue'

import { WarehousePlan } from './types'

const emit = defineEmits(['update:walkableCells'])

const containerRef = useTemplateRef('container')
const stageRef = useTemplateRef<Stage>('stage')
const gridRef = useTemplateRef<Layer>('grid')
const walkableRef = useTemplateRef<Layer>('walkable')
const hoverRef = useTemplateRef<Layer>('hover')

const GRID_CELL_COLOR = 'rgba(0,0,0,0.1)'
const WALKABLE_CELL_COLOR = 'rgba(0, 255, 0, 0.3)'
const { width, height } = useElementSize(containerRef)
const isPainting = ref(false)
const backgroundImage = ref<HTMLImageElement | null>(null)
const paintMode = ref<boolean | null>(null) // true for adding cells, false for removing
const walkableCells = ref<Set<string>>(new Set())
const hoverCell = ref({ x: 0, y: 0 })

onMounted(() => {
	// Load floor plan image into Konva's image layer
	if (plan.value.image) {
		const img = new Image()
		img.onload = () => {
			backgroundImage.value = img
		}
		img.src = plan.value.image
	}

	// Initialize walkable cells from matrix
	walkableCells.value = initializeFromMatrix(plan.value.matrix)

	if (stageRef.value) {
		// Initialize stage event handlers
		const stageLayer = getLayer(stageRef)
		stageLayer?.on('mousemove', updateHoverPosition)
	}
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

// Konva configurations
const stageConfig = computed(
	(): StageConfig => ({
		width: width.value || 1200,
		height: height.value || 800,
	})
)

const imageConfig = computed(
	(): ImageConfig => ({
		image: backgroundImage.value!,
		width: stageConfig.value.width,
		height: stageConfig.value.height,
		listening: false,
	})
)

const gridConfig = computed(
	(): RectConfig => ({
		x: offsetPixels.value.left,
		y: offsetPixels.value.top,
		width: availableDimensions.value.width,
		height: availableDimensions.value.height,
		stroke: GRID_CELL_COLOR,
		strokeWidth: 1,
		listening: false,
	})
)

const hoverConfig = computed(
	(): RectConfig => ({
		x: offsetPixels.value.left + hoverCell.value.x * cellSize.value.width,
		y: offsetPixels.value.top + hoverCell.value.y * cellSize.value.height,
		width: cellSize.value.width,
		height: cellSize.value.height,
		stroke: 'tomato',
		strokeWidth: 2,
		opacity: isHoverValid.value ? 0.5 : 0,
		listening: false,
	})
)

const getHorizontalGridConfig = (index: number): LineConfig => ({
	points: [
		offsetPixels.value.left + index * cellSize.value.width,
		offsetPixels.value.top,
		offsetPixels.value.left + index * cellSize.value.width,
		offsetPixels.value.top + availableDimensions.value.height,
	],
	stroke: GRID_CELL_COLOR,
	strokeWidth: 1,
	listening: false,
})

const getVerticalGridConfig = (index: number): LineConfig => ({
	points: [
		offsetPixels.value.left,
		offsetPixels.value.top + index * cellSize.value.height,
		offsetPixels.value.left + availableDimensions.value.width,
		offsetPixels.value.top + index * cellSize.value.height,
	],
	stroke: GRID_CELL_COLOR,
	strokeWidth: 1,
	listening: false,
})

const getWalkableCellConfig = (x: number, y: number): RectConfig => ({
	x: offsetPixels.value.left + x * cellSize.value.width,
	y: offsetPixels.value.top + y * cellSize.value.height,
	width: cellSize.value.width,
	height: cellSize.value.height,
	fill: WALKABLE_CELL_COLOR,
	listening: false,
})

const offsetGrids = computed(() => {
	const [top, left, bottom, right] = plan.value.offset.split(',').map(v => parseFloat(v) || 0)
	return { top, left, bottom, right }
})

const offsetPixels = computed(() => ({
	top: (offsetGrids.value.top / plan.value.vertical) * stageConfig.value.height!,
	left: (offsetGrids.value.left / plan.value.horizontal) * stageConfig.value.width!,
}))

const availableDimensions = computed(() => {
	const widthOffset = offsetGrids.value.left + offsetGrids.value.right
	const heightOffset = offsetGrids.value.top + offsetGrids.value.bottom
	const availableWidth = stageConfig.value.width! * (1 - widthOffset / plan.value.horizontal)
	const availableHeight = stageConfig.value.height! * (1 - heightOffset / plan.value.vertical)
	return { width: availableWidth, height: availableHeight }
})

const cellSize = computed(() => ({
	width: availableDimensions.value.width / plan.value.horizontal,
	height: availableDimensions.value.height / plan.value.vertical,
}))

const walkableCellsArray = computed(() =>
	Array.from(walkableCells.value).map(cell => {
		const [x, y] = cell.split(',').map(Number)
		return { x, y }
	})
)

const isHoverValid = computed(() => {
	return (
		hoverCell.value.x >= 0 &&
		hoverCell.value.x < plan.value.horizontal &&
		hoverCell.value.y >= 0 &&
		hoverCell.value.y < plan.value.vertical
	)
})

const getLayer = (entity: Readonly<ShallowRef<Stage | Layer | null>>) => entity.value?.getStage()

const toggleWalkable = () => {
	const walkableLayer = getLayer(walkableRef)
	if (!walkableLayer) return
	if (walkableLayer.isVisible()) {
		walkableLayer.hide()
	} else {
		walkableLayer.show()
	}
}

const toggleGrid = () => {
	const gridLayer = getLayer(gridRef)
	if (!gridLayer) return
	if (gridLayer.isVisible()) {
		gridLayer.hide()
	} else {
		gridLayer.show()
	}
}

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

const updateHoverPosition = (e: KonvaEventObject<MouseEvent>) => {
	const stage = e.target.getStage()
	if (!stage) return

	const pointerPosition = stage.getPointerPosition()
	if (!pointerPosition) return

	const adjustedX = pointerPosition.x - offsetPixels.value.left
	const adjustedY = pointerPosition.y - offsetPixels.value.top

	hoverCell.value = {
		x: Math.floor(adjustedX / cellSize.value.width),
		y: Math.floor(adjustedY / cellSize.value.height),
	}

	const hoverLayer = getLayer(hoverRef)
	hoverLayer?.batchDraw()
}

const getCellFromEvent = () => {
	if (isHoverValid.value) return hoverCell.value
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

		const walkableLayer = getLayer(walkableRef)
		walkableLayer?.batchDraw()

		emitUpdate()
	}
}

const emitUpdate = () => {
	window.cur_frm.dirty()
	emit('update:walkableCells', getWalkableCells())
}

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
const getWalkableCells = () => walkableCellsArray.value

// Watch for changes
watch(
	walkableCells,
	() => {
		const walkableLayer = getLayer(walkableRef)
		walkableLayer?.batchDraw()
	},
	{ deep: true }
)

// Expose public methods
defineExpose({
	isCellWalkable,
	getMatrixArray,
	getMatrixString,
	getWalkableCells,
})
</script>

<style scoped>
.toolbar {
	display: flex;
	flex-direction: row-reverse;
	align-items: center;
	gap: 8px;
}

.overlay-dimension {
	position: absolute;
	top: 38px;
	right: 8px;
	background-color: rgba(255, 255, 255, 0.8);
	padding: 4px 8px;
	border-radius: 4px;
	font-size: 14px;
	z-index: 1;
}
</style>
