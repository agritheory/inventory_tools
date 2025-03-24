// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

import { Rect } from 'konva/lib/shapes/Rect'

export type WarehousePlan = {
	company: string
	floor_plan: string
	uom: string
	horizontal: number
	vertical: number
	/**
	 * Offset relative to number of total horizontal and vertical blocks
	 * (in the format "top,left,bottom,right")
	 */
	offset: `${number},${number},${number},${number}`
	matrix?: string
}

export type WarehouseContextMenu = {
	visible: boolean
	x: number
	y: number
	options: { text: string; action?: string }[]
	target?: Rect | null
}

export type WarehouseDialogFields = {
	warehouse: string
	warehouse_length: number
	warehouse_width: number
	warehouse_uom: string
}

export type WarehousePopup = {
	visible: boolean
	x?: number
	y?: number
	title?: string
	length?: number
	width?: number
	accessPoint?: string
}

export type WarehousePlanDetails = {
	warehouse_name: string
	coordinates: string
	rotation: string
	accessible_path: string
}
