<!-- Copyright (c) 2025, AgriTheory and contributors
For license information, please see license.txt-->

# Alternative Workstation Functionality

<div class="byline">
  Rohan Bansal, coleandreoli, IshwaryaM1030, Tyler Matteson, and Francisco Roldán 2026-03-04
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
1. Navigate to **Alternative Workstations Page**.  
2. Select a **Work Order** from the filter.  
3. The system displays all operations under that Work Order, with:  
   - **Primary Workstation** (currently assigned)  
   - **Alternative Workstations** (from the Operation master)  

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
- Updates the assigned workstation in the **Work Order Operation** child table.  
- Saves the change in the database.  
- Refreshes the page to reflect the new assignment.  
