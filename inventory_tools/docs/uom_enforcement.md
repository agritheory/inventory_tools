# UOM Enforcement

By default ERPNext allows a user to select any UOM for any item. If no conversion ratio exists between the UOM selected and the Items stock UOM, ERPNext assumes it should be 1:1. This feature enforces that only valid UOMs are used and are able to be selected in the first place. If an item has no way to be understood in "Linear Feet" and "Volts". 

## Configuration
To enable this feature, the "Enforce UOMs" bos in Inventory Tools Settings should be checked.

## Extending or Overriding This Feature
If you don't like that you can't enter arbitrary UOMs in a specific doctype, you can override it your custom app. For example, let's override the Opportunity doctype.

```python
# custom_app/hooks.py
inventory_tools_uom_enforcement = {
  "Opportunity": {"Opportunity Item": {"items": []}},
}
```
Here we have removed "uom" from the list of fields to check.

To extend this to your own doctype, follow the pattern established in the configuration object:

```python
# custom_app/hooks.py
inventory_tools_uom_enforcement = {
	"My Custom Doctype": {
		"My Custom Doctype": ["uom"] # a UOM field at parent/ form level
		"My Custom Doctype Child Table": {"items": ["uom", "weight_uom", ]}, # UOM fields in a child table
		"My Second Custom Doctype Child Table": {"mistakes": ["uom", "weight_uom", ]}, # UOM fields in a second child table
	},
}
```

