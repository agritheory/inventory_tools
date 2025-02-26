// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

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

export type WarehouseDialogFields = {
	warehouse: string
	warehouse_length: number
	warehouse_width: number
	warehouse_uom: string
}
