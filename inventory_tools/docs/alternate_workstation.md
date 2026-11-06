<!-- Copyright (c) 2025, AgriTheory and contributors
For license information, please see license.txt-->

# Alternative Workstation Functionality

<div class="byline">
  Rohan Bansal, coleandreoli, IshwaryaM1030, Tyler Matteson, and Francisco Roldán 2026-09-15
</div>


## Overview
Manufacturing operations often face bottlenecks when a workstation is unavailable (maintenance, overload, breakdown).  
To ensure flexibility, Inventory Tools now supports **Alternative Workstations**.  

- Each **Operation** can be linked with multiple alternative workstations.  
- A **Work Order** inherits these alternatives.  
- Users can quickly switch from the **primary workstation** to an **alternative** through the **Alternative Workstations Page**.  

---

## How It Works

### 1. Define Alternatives in Operation
In the **Operation Doctype**, a field **Alternative Workstations** is available.  
This allows selecting multiple workstations that can perform the same operation.  

**Example:**  
- Operation: Cutting  
- Primary Workstation: **ST1**  
- Alternatives: **ST2, ST3**

---

### 2. Work Order Setup
When a **Work Order** is created:  
- Each operation inherits its **primary workstation**.  
- Alternatives remain available for assignment if needed.  

---

### 3. Alternative Workstations Page
Steps:  
1. Navigate to **Alternative Workstations Page** (desk route `alternative-workstation`).  
2. Select a **Work Order** from the filter, or open the page with a work order in the URL, for example `?work_order=MFG-WO-2025-00001`. The URL and the filter stay in sync when you change the selection.  
3. The system displays all operations under that Work Order, with:  
   - **Primary Workstation** (currently assigned)  
   - **Alternative Workstations**, subject to the **Allow Alternative Workstations** setting in **Inventory Tools Settings** for your company:
     - **Do Not Allow Alternative Workstations:** no alternatives are offered.
     - **Allow Manually Defined Alternative Workstations:** the BOM's workstation for the operation, the Operation's default workstation, and the Operation's **Alternative Workstations** table.
     - **Allow Alternative Workstations Based on Workstation Type:** every workstation with the same **Workstation Type** as the Operation's default workstation.

Operations that are already completed (the Work Order operation is **Completed**, or a Job Card for it has been submitted) are marked with a checkmark. Their alternatives are still listed, but the **“Use Alternative”** buttons are disabled.

---

### 4. Assigning an Alternative
For each operation row, available alternatives are shown with a **“Use Alternative”** button.  

- ### Rendering
- **Primary Workstation Card**
  - Shows workstation name, next available time, capacity, and planned start.
  - Card color logic:
    - **Purple:** Non-default workstation chosen.
    - **Green:** Default workstation available and earliest option.
    - **Yellow:** Default workstation is busy or not the earliest option.
- **Alternative Workstations**
  - Sorted by earliest availability.

Clicking this button:  
- Requires write permission on the **Work Order**.  
- Updates the assigned workstation, hour rate and planned times in the **Work Order Operation** child table, and recalculates the Work Order's planned operating cost.  
- Updates the workstation on any draft **Job Cards** for that operation. Submitted Job Cards are never changed, since they record where the work was done.  
- Refreshes the page to reflect the new assignment.  

**Caveats**

- **Completed operations can't be reassigned.** Once the operation is completed, its workstation is fixed so operating cost stays tied to where the work happened.
- **Operating cost can change.** Each workstation has its own **Hour Rate** (and, when you use it, [Workstation Operating Cost](./workstation_operating_cost.md) periods). Assigning a different workstation updates the operation’s hour rate and recalculates planned operating cost on the Work Order. Actual manufacturing cost still depends on Job Card time and the rates in effect when you post manufacturing entries. See [Workstation Operating Cost](./workstation_operating_cost.md) for how rates flow into Stock Entries.
- **Same-warehouse alternatives.** The reference workstation for an operation is the workstation on the Work Order's (or Job Card's) **BOM** for that operation, or the Operation's default workstation when the BOM doesn't set one. Alternatives must share the reference workstation's **Warehouse**, or have **Warehouse** left blank. Workstations with a different warehouse are excluded from the link search and from the Alternative Workstations page, and are rejected when you change the workstation on a saved Job Card. This rule doesn't apply when the setting is **Do Not Allow Alternative Workstations**.
- **Workstation warehouses.** A workstation's **Warehouse** can't be a group or disabled warehouse.
- **No stock movement.** Changing workstation does not move inventory. Raw materials are still transferred to the Work Order's **Work In Progress** warehouse, which is why alternatives are limited to the same warehouse.

You can open this page from a submitted **Work Order** or (when enabled in **Inventory Tools Settings**) from a **Job Card**, using the **Alternative Workstations** action under **View**.
