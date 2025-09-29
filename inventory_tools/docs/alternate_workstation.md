<!-- Copyright (c) 2025, AgriTheory and contributors
For license information, please see license.txt-->

# 📘 Alternative Workstation Functionality

## 🔎 Overview
Manufacturing operations often face bottlenecks when a workstation is unavailable (maintenance, overload, breakdown).  
To ensure flexibility, Inventory Tools now supports **Alternative Workstations**.  

- Each **Operation** can be linked with multiple alternative workstations.  
- A **Work Order** inherits these alternatives.  
- Users can quickly switch from the **primary workstation** to an **alternative** through the **Workstation Selection Page**.  

---

## 🏗 How It Works

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

### 3. Workstation Selection Page
Steps:  
1. Navigate to **Workstation Selection Page**.  
2. Select a **Work Order** from the filter.  
3. The system displays all operations under that Work Order, with:  
   - **Primary Workstation** (currently assigned)  
   - **Alternative Workstations** (from the Operation master)  

---

### 4. Assigning an Alternative
For each operation row, available alternatives are shown with a **“Use Alternative”** button.  

Clicking this button:  
- Updates the assigned workstation in the **Work Order Operation** child table.  
- Saves the change in the database.  
- Refreshes the page to reflect the new assignment.  
