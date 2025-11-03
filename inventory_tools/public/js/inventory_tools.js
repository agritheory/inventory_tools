// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

import VueKonva from 'vue-konva'
import { createApp } from 'vue'

import PlantFloor from './wms/PlantFloor.vue'
import WarehousePlan from './wms/WarehousePlan.vue'

frappe.provide('inventory_tools')

inventory_tools.mount_plant_floor = frm => {
	$(frm.fields_dict['floor_layout'].wrapper).html($("<div id='plant-floor-layout'></div>").get(0))
	frm.plant_floor_layout = createApp(PlantFloor)
	inventory_tools.$plant_floor = frm.plant_floor_layout.mount('#plant-floor-layout')
}

inventory_tools.mount_warehouse_plan = frm => {
	$(frm.fields_dict['warehouse_plan'].wrapper).html(
		$('<div id="warehouse-plan" style="min-height: 60vh"></div>').get(0)
	)
	frm.warehouse_plan = createApp(WarehousePlan)
	frm.warehouse_plan.use(VueKonva, { prefix: 'Konva' })
	inventory_tools.$warehouse_plan = frm.warehouse_plan.mount('#warehouse-plan')
}
