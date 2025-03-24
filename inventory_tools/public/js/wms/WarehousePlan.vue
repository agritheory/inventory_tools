<template>
	<div v-if="plan.horizontal && plan.vertical">
		<div class="toolbar">
			<button v-if="gridRef" @click="toggleGrid" class="btn btn-toggle-grid">Toggle Grid</button>
			<button v-if="walkableRef" @click="toggleWalkable" class="btn btn-toggle-walkable">Toggle Walkable</button>
			<button @click="addWarehouse" class="btn btn-primary btn-add-warehouse">Add Warehouse</button>
		</div>

		<div class="overlay">
			<div class="overlay-dimension">{{ plan.horizontal }}x{{ plan.vertical }} {{ plan.uom }}</div>
			<!-- <div v-if="isHoverValid" class="overlay-cell-info">
				Cell: ({{ hoverCell.x }}, {{ hoverCell.y }})
				<span v-if="isCellWalkable(hoverCell.x, hoverCell.y)" class="overlay-cell-status overlay-walkable">
					Walkable
				</span>
				<span v-else class="overlay-cell-status overlay-non-walkable">Non-walkable</span>
			</div> -->
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

			<!-- Context Menu -->
			<div
				v-if="contextMenu.visible"
				v-on-click-outside="hideContextMenu"
				class="context-menu"
				:style="{
					top: `${contextMenu.y}px`,
					left: `${contextMenu.x}px`,
				}">
				<div
					v-for="(option, index) in contextMenu.options"
					v-html="option.text"
					:key="index"
					class="context-menu-item"
					@click="option.action && runContextAction(option.action)" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { vOnClickOutside } from '@vueuse/components'
import { useElementSize } from '@vueuse/core'
import type { Layer } from 'konva/lib/Layer'
import type { KonvaEventObject } from 'konva/lib/Node'
import type { ImageConfig } from 'konva/lib/shapes/Image'
import type { LineConfig } from 'konva/lib/shapes/Line'
import { Rect, type RectConfig } from 'konva/lib/shapes/Rect'
import { Stage, type StageConfig } from 'konva/lib/Stage'
import { ref, computed, onMounted, watch, useTemplateRef, type ShallowRef } from 'vue'

import type { WarehouseContextMenu, WarehouseDialogFields, WarehousePlan, WarehousePlanDetails } from './types'

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
const backgroundImage = ref<HTMLImageElement | null>(null)
const contextMenu = ref<WarehouseContextMenu>({ visible: false, x: 0, y: 0, options: [] })
const hoverCell = ref({ x: 0, y: 0 })
const isDraggingWarehouse = ref(false)
const isPainting = ref(false)
const paintMode = ref<boolean | null>(null) // true for adding cells, false for removing
const walkableCells = ref<Set<string>>(new Set())
const settingAccessibleCellFor = ref<Rect | null>(null)

onMounted(async () => {
	// Load floor plan image into Konva's image layer
	if (plan.value.image) {
		const img = new Image()
		img.onload = () => {
			backgroundImage.value = img
		}
		img.src = plan.value.image
	}

	// Initialize walkable cells from matrix
	walkableCells.value = initializePath(plan.value.matrix)
	await initializeWarehouses()

	if (stageRef.value) {
		// Initialize stage mouse handlers
		const stageLayer = getLayer(stageRef)
		stageLayer!.on('mousemove', updateHoverPosition)
		stageLayer!.on('click', setAccessCell)
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
		stroke: settingAccessibleCellFor.value ? 'lime' : 'tomato',
		strokeWidth: 2,
		opacity: isHoverValid.value
			? settingAccessibleCellFor.value && isCellWalkable(hoverCell.value.x, hoverCell.value.y)
				? 0.7
				: 0.5
			: 0,
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

const initializePath = (matrixString?: string) => {
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

const initializeWarehouses = async () => {
	const { message: warehouses } = await frm.value.call('get_plan_warehouses')
	for (const warehouse of warehouses) {
		const [x, y, length, width] = warehouse.warehouse_plan_coordinates.split(',').map(Number)
		const adjustedX = offsetPixels.value.left + x * cellSize.value.width
		const adjustedY = offsetPixels.value.top + y * cellSize.value.height

		addWarehouseRect(warehouse.name, length, width, adjustedX, adjustedY, warehouse.rotation, warehouse.accessible_path)
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

	redrawLayer(hoverRef)
}

// #################################################################
// ######################## TOGGLE ACTIONS #########################
// #################################################################
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

// #################################################################
// ######################### CONTEXT MENU ##########################
// #################################################################
const showContextMenu = (event: KonvaEventObject<MouseEvent, Rect>, shape: Rect) => {
	event.evt.preventDefault()

	// Get the position of the context menu
	const stage = event.target.getStage()
	if (!stage) return
	const pointerPosition = stage.getPointerPosition()
	if (!pointerPosition) return

	const { warehouse_name, warehouse_length, warehouse_width, accessible_path } = shape.getAttr('warehouseData')

	// Format the accessible path for display
	let accessCell = 'Not Set'
	if (accessible_path) {
		const [pathX, pathY] = accessible_path.split(',').map(Number)
		accessCell = `(${pathX}, ${pathY})`
	}

	contextMenu.value = {
		visible: true,
		x: pointerPosition.x,
		y: pointerPosition.y,
		options: [
			{
				text: `
					<p><strong>${warehouse_name || 'Warehouse'}</strong></p>
					<p>${warehouse_length.toFixed(2)} x ${warehouse_width.toFixed(2)} ${doc.value.uom} (LxW)</p>
					<p style="margin-bottom: 0">Accessible From: ${accessCell}</p>
				`,
			},
			{ text: `Edit`, action: 'edit' },
			{ text: 'Rotate', action: 'rotate' },
			{ text: 'Set Access Cell', action: 'set-access' },
			{ text: 'Delete', action: 'delete' },
		],
		target: shape,
	}
}

const hideContextMenu = () => {
	contextMenu.value.visible = false
	contextMenu.value.target = null
}

const runContextAction = (action: string) => {
	const shape = contextMenu.value.target as Rect | null
	if (shape) {
		switch (action) {
			case 'edit':
				editWarehouse(shape)
				break
			case 'rotate':
				rotateWarehouse(shape)
				break
			case 'set-access':
				startAccessCellSelection(shape)
				break
			case 'delete':
				deleteWarehouse(shape)
				break
		}
	}
	hideContextMenu()
}

const startAccessCellSelection = (shape: Rect) => {
	settingAccessibleCellFor.value = shape
	frappe.show_alert('Click on a walkable cell to set as the nearest accessible cell', 15)
}

const setAccessCell = (event: KonvaEventObject<MouseEvent>) => {
	if (settingAccessibleCellFor.value) {
		const cell = getCellFromEvent()
		if (cell && isCellWalkable(cell.x, cell.y)) {
			setWarehouseAccessPath(settingAccessibleCellFor.value as Rect, cell.x, cell.y)
			settingAccessibleCellFor.value = null
			frm.value.dirty()
		}
	}
}

const setWarehouseAccessPath = (shape: Rect, x: number, y: number) => {
	const warehouseData = shape.getAttr('warehouseData')
	shape.setAttr('warehouseData', {
		...warehouseData,
		accessible_path: `${x},${y}`,
	})
	frappe.show_alert(`Path set for ${warehouseData.warehouse_name} to (${x}, ${y})`, 3)
}

const showWarehouseDialog = (
	action: 'Add' | 'Edit',
	callback: (values: WarehouseDialogFields) => void,
	title?: string,
	btnLabel?: string,
	defaults?: Record<string, any>
) => {
	const dialog = frappe.prompt(
		[
			{
				label: 'Warehouse',
				fieldname: 'warehouse',
				fieldtype: 'Link',
				options: 'Warehouse',
				default: action === 'Edit' ? defaults?.warehouse || '' : '',
				read_only: action === 'Edit',
				get_query: () => ({ filters: { company: doc.value.company, is_group: false } }),
				change: async () => {
					const values = dialog.get_values()
					if (values.warehouse) {
						const { message } = await frm.value.call('get_warehouse_dimensions', {
							warehouse: values.warehouse,
						})
						dialog.set_value('warehouse_length', message.item_length || 0)
						dialog.set_value('warehouse_width', message.item_width || 0)
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
				default: action === 'Edit' ? defaults?.warehouse_length || 0 : 0,
				depends_on: 'eval:doc.warehouse',
			},
			{
				label: 'Width',
				fieldname: 'warehouse_width',
				fieldtype: 'Float',
				default: action === 'Edit' ? defaults?.warehouse_width || 0 : 0,
				depends_on: 'eval:doc.warehouse',
			},
			{
				label: 'Dimension UOM',
				fieldname: 'warehouse_uom',
				fieldtype: 'Link',
				options: 'UOM',
				default: action === 'Edit' ? defaults?.warehouse_uom || doc.value.uom : doc.value.uom,
				read_only: true,
			},
		],
		callback,
		title,
		btnLabel
	)
}

// #################################################################
// ####################### WAREHOUSE ACTIONS #######################
// #################################################################
const addWarehouse = () => {
	showWarehouseDialog(
		'Add',
		(values: WarehouseDialogFields) => {
			addWarehouseRect(values.warehouse, values.warehouse_length, values.warehouse_width)
		},
		'Add Warehouse'
	)
}

const addWarehouseRect = (
	name: string,
	length: number,
	width: number,
	x?: number,
	y?: number,
	rotation?: number,
	accessiblePath?: string
) => {
	const warehouseRect: Rect = new Rect({
		x: x || canvasDimensions.value.width / 2,
		y: y || canvasDimensions.value.height / 2,
		width: length * cellSize.value.width,
		height: width * cellSize.value.height,
		fill: 'rgba(0, 0, 255, 0.3)',
		rotation: rotation || 0,
		draggable: true,
		listening: true,
		dragBoundFunc: position => {
			// set the bounds of dragging to be inside the drawn canvas, minus the shape's dimensions
			const minPos = { x: offsetPixels.value.left, y: offsetPixels.value.top }
			const maxPos = {
				x: minPos.x + canvasDimensions.value.width - warehouseRect.width(),
				y: minPos.y + canvasDimensions.value.height - warehouseRect.height(),
			}

			return {
				x: Math.max(minPos.x, Math.min(position.x, maxPos.x)),
				y: Math.max(minPos.y, Math.min(position.y, maxPos.y)),
			}
		},
	})

	// Add custom data to the warehouse rect
	warehouseRect.setAttr('warehouseData', {
		warehouse_name: name,
		warehouse_length: length,
		warehouse_width: width,
		warehouse_rotation: rotation || 0,
		accessible_path: accessiblePath || '',
	})

	warehouseRect.on('contextmenu', event => {
		event.evt.preventDefault()
		event.evt.stopPropagation()
		event.cancelBubble = true
		showContextMenu(event, warehouseRect)
	})

	// Since drag event handlers are not configurable while building the shape,
	// adding drag event handlers individually to track dragging state
	warehouseRect.on('dragstart', () => (isDraggingWarehouse.value = true))
	warehouseRect.on('dragend', () => {
		frm.value.dirty()
		isDraggingWarehouse.value = false
	})

	// A `mousedown` event on the shape will also trigger a `mousedown` event on the stage
	// which will start painting cells. To prevent this, we cancel the bubble.
	warehouseRect.on('mousedown', event => (event.cancelBubble = true))

	// Add the warehouse shape to the warehouse layer
	const warehouseLayer = getLayer(warehouseRef) as unknown as Layer | undefined
	warehouseLayer?.add(warehouseRect)
}

const editWarehouse = (shape: Rect) => {
	const warehouseData = shape.getAttr('warehouseData')
	showWarehouseDialog(
		'Edit',
		(values: WarehouseDialogFields) => {
			const widthDelta = values.warehouse_length * cellSize.value.width - shape.width()
			const heightDelta = values.warehouse_width * cellSize.value.height - shape.height()

			shape
				.width(values.warehouse_length * cellSize.value.width)
				.height(values.warehouse_width * cellSize.value.height)
				.move({ x: -widthDelta, y: -heightDelta })
				.setAttr('warehouseData', {
					...warehouseData,
					warehouse_name: values.warehouse,
					warehouse_length: values.warehouse_length,
					warehouse_width: values.warehouse_width,
				})

			redrawLayer(warehouseRef)
		},
		'Edit Warehouse',
		undefined,
		{
			warehouse: warehouseData.warehouse_name,
			warehouse_length: warehouseData.warehouse_length,
			warehouse_width: warehouseData.warehouse_width,
			warehouse_uom: doc.value.uom,
		}
	)
}

const rotateWarehouse = (shape: Rect) => {
	const warehouseData = shape.getAttr('warehouseData')
	const currentRotation = warehouseData.warehouse_rotation || 0
	frappe.prompt(
		[
			{
				label: 'Rotation (degrees)',
				fieldname: 'rotate_by',
				fieldtype: 'Float',
				default: currentRotation,
			},
		],
		(values: { rotate_by: number }) => {
			const delta = values.rotate_by - currentRotation
			shape.rotate(delta).setAttr('warehouseData', {
				...warehouseData,
				warehouse_rotation: values.rotate_by,
			})
			redrawLayer(warehouseRef)
		},
		'Rotate Warehouse'
	)
}

const deleteWarehouse = (shape: Rect) => {
	const { warehouse_name } = shape.getAttr('warehouseData')
	frappe.confirm(`Are you sure you want to remove <strong>${warehouse_name}</strong> from the plan?`, () => {
		shape.destroy()
		redrawLayer(warehouseRef)
	})
}

// #################################################################
// ######################### DRAW ACTIONS ##########################
// #################################################################
const getCellFromEvent = () => {
	if (isHoverValid.value) return hoverCell.value
}

const startPainting = (event: KonvaEventObject<MouseEvent>) => {
	if (isDraggingWarehouse.value || settingAccessibleCellFor.value) return
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

const redrawLayer = (ref: Readonly<ShallowRef<Stage | Layer | null>>) => {
	const layer = getLayer(ref)
	layer?.batchDraw()
	frm.value.dirty()
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

		redrawLayer(walkableRef)
		emitUpdate()
	}
}

const emitUpdate = () => {
	frm.value.dirty()
	emit('update:walkableCells', getWalkableCells())
}

// #################################################################
// ######################### HELPER METHODS ########################
// #################################################################
const getWalkableArray = () => {
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

const getWarehouseArray = () => {
	const warehouseLayer = getLayer(warehouseRef) as unknown as Layer | undefined
	const children = warehouseLayer?.children || []
	const warehouseDetails: WarehousePlanDetails[] = []

	for (const child of children) {
		const warehouseData = child.getAttr('warehouseData')
		const { x, y } = child.getPosition()
		const horizontalGrid = (x - offsetPixels.value.left) / cellSize.value.width
		const verticalGrid = (y - offsetPixels.value.top) / cellSize.value.height

		warehouseDetails.push({
			warehouse_name: warehouseData.warehouse_name,
			coordinates: `${horizontalGrid.toFixed(2)},${verticalGrid.toFixed(2)},${warehouseData.warehouse_length},${
				warehouseData.warehouse_width
			}`,
			rotation: warehouseData.warehouse_rotation,
			accessible_path: warehouseData.accessible_path || '',
		})
	}

	return warehouseDetails
}

const isCellWalkable = (x: number, y: number) => walkableCells.value.has(`${x},${y}`)
const getWalkableString = () => JSON.stringify(getWalkableArray())
const getWalkableCells = () => walkableCellsArray.value

// Watch for changes
watch(walkableCells, () => redrawLayer(walkableRef), { deep: true })

// Expose public methods
defineExpose({
	isCellWalkable,
	getWalkableArray,
	getWalkableString,
	getWalkableCells,
	getWarehouseArray,
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

.overlay-cell-info {
	position: absolute;
	top: 70px;
	right: 8px;
	background-color: rgba(255, 255, 255, 0.8);
	padding: 4px 8px;
	border-radius: 4px;
	font-size: 14px;
	z-index: 1;
}

.overlay-cell-status {
	margin-left: 4px;
	font-weight: bold;
	border-radius: 3px;
	padding: 1px 4px;
}

.overlay-walkable {
	background-color: rgba(0, 255, 0, 0.2);
	color: green;
}

.overlay-non-walkable {
	background-color: rgba(255, 0, 0, 0.1);
	color: #c53030;
}

.context-menu {
	position: absolute;
	background: white;
	border: 1px solid #ccc;
	box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.2);
	border-radius: 4px;
	z-index: 1000;
	min-width: 150px;
}

.context-menu-item {
	padding: 8px 12px;
	cursor: pointer;
}

.context-menu-item:hover {
	background-color: #f0f0f0;
}

.context-menu-item:not(:last-child) {
	border-bottom: 1px solid #eee;
}
</style>
