# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

suppliers = [
	(
		"Freedom Provisions",
		None,
		None,
		None,
		"Net 30",
		{
			"address_line1": "16 Margrave",
			"city": "Carlisle",
			"state": "NH",
			"country": "United States",
			"pincode": "57173",
		},
	),
	(
		"Unity Bakery Supply",
		None,
		None,
		None,
		"Net 30",
		{
			"address_line1": "34 Pinar St",
			"city": "Unity",
			"state": "RI",
			"country": "United States",
			"pincode": "34291",
		},
	),
	(
		"Chelsea Fruit Co",
		None,
		None,
		None,
		"Net 30",
		{
			"address_line1": "67C Sweeny Street",
			"city": "Chelsea",
			"state": "MA",
			"country": "United States",
			"pincode": "89077",
		},
	),
	(
		"Credible Contract Baking",
		None,
		None,
		None,
		"Net 30",
		{
			"address_line1": "4 Crumb Circle",
			"city": "Belmont",
			"state": "MA",
			"country": "United States",
			"pincode": "89074",
		},
	),
	(
		"Southern Fruit Supply",
		None,
		None,
		None,
		"Net 30",
		{
			"address_line1": "10001 Pineapple Way",
			"city": "Largo",
			"state": "TX",
			"country": "United States",
			"pincode": "89574",
		},
	),
]

workstations = [
	("Mix Pie Crust Station", "20", "mixer.png", "mixer.png"),
	("Roll Pie Crust Station", "20", "rolling.png", "rolling.png"),
	("Make Pie Filling Station", "20", "table.png", "table.png"),
	("Cooling Station", "100", "rack.png", "rack.png"),
	("Box Pie Station", "100", "box.png", "box.png"),
	("Baking Station", "20", "oven.png", "oven.png"),
	("Assemble Pie Station", "20", "table.png", "table.png"),
	("Mix Pie Filling Station", "20", "mixer.png", "mixer.png"),
	("Packaging Station", "2", "box.png", "box.png"),
	("Food Prep Table 2", "10", "table.png", "table.png"),
	("Food Prep Table 1", "5", "table.png", "table.png"),
	("Range Station", "20", "range.png", "range.png"),
	("Cooling Racks Station", "80", "rack.png", "rack.png"),
	("Refrigerator Station", "200", "fridge.png", "fridge.png"),
	("Oven Station", "20", "oven.png", "oven.png"),
	("Mixer Station", "10", "mixer.png", "mixer.png"),
]

operations = [
	(
		"Gather Pie Crust Ingredients",
		"Food Prep Table 2",
		"5",
		"""- Remove flour, salt, and a pie tins from store room
	- Remove butter and ice water from refrigerator
	- Place ingredients at workstation
	- Measure amounts for batch size into mixing bowl""",
		["Food Prep Table 1"],
	),
	(
		"Gather Pie Filling Ingredients",
		"Food Prep Table 1",
		"5",
		"""- Remove fruit and butter from refrigerator
	- Remove sugar and cornstarch
	- Get water from sink
	- Measure ingredients and place in pot, excluding 1/4 of fruit and butter""",
		["Food Prep Table 2"],
	),
	(
		"Assemble Pie Op",
		"Food Prep Table 2",
		"5",
		"""- Use fresh pie filling or remove from refrigerator
	- Remove rolled pie crusts from refrigerator
	- Fill bottom crust with filling
	- Create decorative cut out for top crust
	- Layer top crust over bottom crust / filling and create a crimped seal""",
		["Food Prep Table 1", "Assemble Pie Station"],
	),
	(
		"Cook Pie Filling Operation",
		"Range Station",
		"5",
		"""- Bring ingredients to simmer and cook for 15 minutes
	- Remove from heat and mix in remaining 1/4 berries and butter
	- Store in refrigerator if not using immediately""",
	),
	(
		"Mix Dough Op",
		"Mixer Station",
		"5",
		"""- Combine flour, butter, salt, and ice water in mixer
	- Pulse for 30 seconds
	- Divide into equal-sized portions, one portion for each pie crust being made
	- Put in refrigerator""",
		["Mix Pie Crust Station", "Mix Pie Filling Station"],
	),
	("Box Pie Op", "Packaging Station", "5", "- Place pie into box for sale"),
	(
		"Roll Pie Crust Op",
		"Food Prep Table 2",
		"5",
		"""- Remove chilled pie crust portions from refrigerator
	- Separate each portion into two (one for bottom crust, one for top)
	- Flour board and roll out each portion into a circle
	- Place bottom crust into pie tin, then layer a piece of parchment paper, followed by the top crust""",
		["Food Prep Table 1", "Roll Pie Crust Station"],
	),
	("Divide Dough Op", "Food Prep Table 2", "1", "Divide Dough Op", ["Food Prep Table 1"]),
	(
		"Bake Op",
		"Oven Station",
		"1",
		"""- Place assembled pies into oven
	- Bake at 375F for 50 minutes
	- Remove from oven""",
		["Baking Station"],
	),
	(
		"Chill Pie Crust Op",
		"Refrigerator Station",
		"1",
		"- Chill pie crust for at least 30 minutes",
		["Cooling Station", "Cooling Racks Station"],
	),
	(
		"Cool Pie Op",
		"Cooling Racks Station",
		"1",
		"Cool baked pies for at least 30 minutes before boxing",
		["Cooling Station", "Refrigerator Station"],
	),
	(
		"Assemble Pocket Op",
		"Food Prep Table 1",
		"5",
		"""- Fold 3 poppers into dough pocket""",
	),
	(
		"Assemble Popper Op",
		"Food Prep Table 1",
		"5",
		"""- Top dough bite with fruit""",
	),
	(
		"Assemble Combination Product",
		"Food Prep Table 1",
		"5",
		"""- Tower: package one pie and one pocket, and one popper
    - Pocketful of Bay: package one pocket with two poppers""",
	),
]


attributes = {
	"Ambrosia Pie": {
		"Fruits": ["Hairless Rambutan", "Cloudberry", "Tayberry"],
		"Price": 11.00,
		"Color": ["Blue", "Red"],
		"Brand": "Chelsea Fruit Co",
	},
	"Double Plum Pie": {
		"Fruits": ["Cocoplum", "Damson Plum"],
		"Price": 10.50,
		"Color": ["Purple"],
		"Brand": "Chelsea Fruit Co",
	},
	"Gooseberry Pie": {
		"Fruits": "Gooseberry",
		"Price": 12.00,
		"Color": ["Yellow"],
		"Brand": "Chelsea Fruit Co",
	},
	"Kaduka Key Lime Pie": {
		"Fruits": ["Kaduka Lime", "Limequat"],
		"Price": 11.50,
		"Color": ["Green", "Yellow"],
		"Brand": "Chelsea Fruit Co",
	},
	"Tayberry": {
		"Color": ["Red"],
	},
	"Limequat": {
		"Color": ["Yellow", "Green"],
	},
	"Kaduka Lime": {
		"Color": ["Green"],
	},
	"Hairless Rambutan": {
		"Color": ["Red"],
	},
	"Gooseberry": {
		"Color": ["Yellow"],
	},
	"Damson Plum": {
		"Color": ["Purple"],
	},
	"Cocoplum": {
		"Color": ["Purple", "Black"],
	},
	"Bayberry": {
		"Color": ["Red", "Green", "Blue"],
	},
	"Sugar": {
		"Color": ["White"],
	},
	"Salt": {
		"Color": ["White"],
	},
	"Flour": {
		"Color": ["White"],
	},
	"Cornstarch": {
		"Color": ["White"],
	},
	"Butter": {
		"Color": ["Yellow"],
	},
	"Cloudberry": {
		"Color": ["Yellow", "Red"],
	},
}
