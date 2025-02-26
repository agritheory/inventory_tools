<template>
	<div v-if="plan.horizontal && plan.vertical">
		<div class="toolbar">
			<button v-if="walkableRef" @click="toggleWalkable" class="btn btn-toggle-walkable">Toggle Walkable</button>
			<button v-if="gridRef" @click="toggleGrid" class="btn btn-toggle-grid">Toggle Grid</button>
			<button @click="addWarehouse" class="btn btn-primary btn-add-warehouse">Add Warehouse</button>
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
					<konva-line v-for="index in plan.horizontal - 1" :key="`v-${index}`" :config="getVerticalLineConfig(index)" />

					<!-- Horizontal Grid Lines -->
					<konva-line v-for="index in plan.vertical - 1" :key="`h-${index}`" :config="getHorizontalLineConfig(index)" />
				</konva-layer>

				<!-- Walkable Cells Layer -->
				<konva-layer ref="walkable">
					<konva-rect
						v-for="cell in walkableCellsArray"
						:key="`cell-${cell.x}-${cell.y}`"
						:config="getWalkableCellConfig(cell.x, cell.y)" />
				</konva-layer>

				<!-- Warehouse Layer -->
				<konva-layer ref="warehouse" />

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
import { Rect, type RectConfig } from 'konva/lib/shapes/Rect'
import { Stage, type StageConfig } from 'konva/lib/Stage'
import { ref, computed, onMounted, watch, useTemplateRef, type ShallowRef } from 'vue'

import { WarehouseDialogFields, WarehousePlan } from './types'

declare const frappe: any

const emit = defineEmits(['update:walkableCells'])

const containerRef = useTemplateRef('container')
const stageRef = useTemplateRef<Stage>('stage')
const gridRef = useTemplateRef<Layer>('grid')
const walkableRef = useTemplateRef<Layer>('walkable')
const warehouseRef = useTemplateRef<Layer>('warehouse')
const hoverRef = useTemplateRef<Layer>('hover')

const GRID_CELL_COLOR = 'rgba(0,0,0,0.1)'
const WALKABLE_CELL_COLOR = 'rgba(0, 255, 0, 0.3)'
const { width, height } = useElementSize(containerRef)
const isPainting = ref(false)
const isDraggingWarehouse = ref(false)
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
		// Initialize stage mouse handlers
		const stageLayer = getLayer(stageRef)
		stageLayer!.on('mousemove', updateHoverPosition)
	}
})

const frm = computed(() => {
	return window.cur_frm
})

const doc = computed(() => {
	return frm.value.doc as WarehousePlan
})

const plan = computed(() => {
	const warehousePlan = doc.value
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
		width: canvasDimensions.value.width,
		height: canvasDimensions.value.height,
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

const getVerticalLineConfig = (index: number): LineConfig => {
	const fixedX = offsetPixels.value.left + index * cellSize.value.width
	const startY = offsetPixels.value.top
	const endY = offsetPixels.value.top + canvasDimensions.value.height
	return {
		points: [fixedX, startY, fixedX, endY],
		stroke: GRID_CELL_COLOR,
		strokeWidth: 1,
		listening: false,
	}
}

const getHorizontalLineConfig = (index: number): LineConfig => {
	const fixedY = offsetPixels.value.top + index * cellSize.value.height
	const startX = offsetPixels.value.left
	const endX = offsetPixels.value.left + canvasDimensions.value.width
	return {
		points: [startX, fixedY, endX, fixedY],
		stroke: GRID_CELL_COLOR,
		strokeWidth: 1,
		listening: false,
	}
}

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

const canvasDimensions = computed(() => {
	const widthOffset = offsetGrids.value.left + offsetGrids.value.right
	const heightOffset = offsetGrids.value.top + offsetGrids.value.bottom
	const canvasWidth = stageConfig.value.width! * (1 - widthOffset / plan.value.horizontal)
	const canvasHeight = stageConfig.value.height! * (1 - heightOffset / plan.value.vertical)
	return { width: canvasWidth, height: canvasHeight }
})

const cellSize = computed(() => ({
	width: canvasDimensions.value.width / plan.value.horizontal,
	height: canvasDimensions.value.height / plan.value.vertical,
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

const addWarehouse = () => {
	const dialog = frappe.prompt(
		[
			{
				label: 'Warehouse',
				fieldname: 'warehouse',
				fieldtype: 'Link',
				options: 'Warehouse',
				get_query: () => ({ filters: { company: doc.value.company, is_group: false } }),
				change: async () => {
					const values = dialog.get_values()
					if (values.warehouse) {
						const response = await frappe.xcall(
							'inventory_tools.inventory_tools.doctype.warehouse_plan.warehouse_plan.get_warehouse_dimensions',
							{
								warehouse: values.warehouse,
								plan_uom: doc.value.uom,
							}
						)
						dialog.set_value('warehouse_length', response.item_length || 0)
						dialog.set_value('warehouse_width', response.item_width || 0)
					} else {
						dialog.set_value('warehouse_length', 0)
						dialog.set_value('warehouse_width', 0)
					}
				},
			},
			{
				label: 'Length',
				fieldname: 'warehouse_length',
				fieldtype: 'Float',
				default: 0,
				depends_on: 'eval:doc.warehouse',
			},
			{
				label: 'Width',
				fieldname: 'warehouse_width',
				fieldtype: 'Float',
				default: 0,
				depends_on: 'eval:doc.warehouse',
			},
			{
				label: 'Dimension UOM',
				fieldname: 'warehouse_uom',
				fieldtype: 'Link',
				options: 'UOM',
				default: doc.value.uom,
				read_only: true,
			},
		],
		(values: WarehouseDialogFields) => {
			const warehouseRect = new Rect({
				x: 0,
				y: 0,
				width: values.warehouse_length * cellSize.value.width,
				height: values.warehouse_width * cellSize.value.height,
				fill: 'rgba(0, 0, 255, 0.3)',
				draggable: true,
				dragBoundFunc: function (position) {
					// TODO: do something with the final position
					const newX = Math.max(0, Math.min(position.x, canvasDimensions.value.width - this.width()))
					const newY = Math.max(0, Math.min(position.y, canvasDimensions.value.height - this.height()))
					return { x: newX, y: newY }
				},
			})

			// Since drag event handlers are not configurable while building the shape,
			// adding drag event handlers individually to track dragging state
			warehouseRect.on('dragstart', () => (isDraggingWarehouse.value = true))
			warehouseRect.on('dragend', () => (isDraggingWarehouse.value = false))

			// A `mousedown` event on the shape will also trigger a `mousedown` event on the stage
			// which will start painting cells. To prevent this, we cancel the bubble.
			warehouseRect.on('mousedown', event => (event.cancelBubble = true))

			// Add the warehouse shape to the warehouse layer
			const warehouseLayer = getLayer(warehouseRef) as unknown as Layer
			warehouseLayer.add(warehouseRect)
		},
		'Add Warehouse'
	)
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
	} catch (error) {
		console.warn('Error parsing matrix string:', error)
		return cells
	}
}

const updateHoverPosition = (event: KonvaEventObject<MouseEvent>) => {
	const stage = event.target.getStage()
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

const startPainting = (event: KonvaEventObject<MouseEvent>) => {
	if (isDraggingWarehouse.value) return
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
	if (!isPainting.value || paintMode.value === null || isDraggingWarehouse.value) return
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
