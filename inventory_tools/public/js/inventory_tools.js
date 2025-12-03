// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

import VueKonva from 'vue-konva'
import { createApp } from 'vue'

import WarehousePlan from './wms/WarehousePlan.vue'
import './faceted_search/faceted_search.js'

frappe.provide('inventory_tools')

inventory_tools.mount_warehouse_plan = frm => {
	$(frm.fields_dict['warehouse_plan'].wrapper).html(
		$('<div id="warehouse-plan" style="min-height: 60vh"></div>').get(0)
	)
	frm.warehouse_plan = createApp(WarehousePlan)
	frm.warehouse_plan.use(VueKonva, { prefix: 'Konva' })
	inventory_tools.$warehouse_plan = frm.warehouse_plan.mount('#warehouse-plan')
}
