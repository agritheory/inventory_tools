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
<<<<<<< HEAD
=======

<<<<<<< HEAD
items_stockentry = {
	"Butter": {"qty": 46, "warehouse": "Refrigerator - APC"},
	"Cornstarch": {"qty": 2, "warehouse": "Storeroom - APC"},
	"Flour": {"qty": 68, "warehouse": "Storeroom - APC"},
	"Kaduka Lime": {"qty": 20, "warehouse": "Refrigerator - APC"},
	"Limequat": {"qty": 10, "warehouse": "Refrigerator - APC"},
	"Parchment Paper": {"qty": 80, "warehouse": "Storeroom - APC"},
	"Pie Tin": {"qty": 80, "warehouse": "Storeroom - APC"},
	"Pie Box": {"qty": 80, "warehouse": "Storeroom - APC"},
	"Salt": {"qty": 1, "warehouse": "Storeroom - APC"},
	"Sugar": {"qty": 8, "warehouse": "Storeroom - APC"},
	"Water": {"qty": 20, "warehouse": "Kitchen - APC"},
	"Cocoplum": {"qty": 45, "warehouse": "Refrigerator - APC"},
	"Damson Plum": {"qty": 45, "warehouse": "Refrigerator - APC"},
	"Cloudberry": {"qty": 45, "warehouse": "Refrigerator - APC"},
	"Hairless Rambutan": {"qty": 30, "warehouse": "Storeroom - APC"},
	"Tayberry": {"qty": 15, "warehouse": "Refrigerator - APC"},
	"Gooseberry": {"qty": 30, "warehouse": "Refrigerator - APC"},
}
>>>>>>> 8d8df6d (warehouse)
=======
items_stockentry = [
	{"item_code": "Butter", "qty": 44, "warehouse": "Refrigerator - APC"},
	{"item_code": "Bayberry", "qty": 82, "warehouse": "Refrigerator - APC"},
	{"item_code": "Cornstarch", "qty": 2, "warehouse": "Storeroom - APC"},
	{"item_code": "Flour", "qty": 71, "warehouse": "Storeroom - APC"},
	{"item_code": "Parchment Paper", "qty": 60, "warehouse": "Storeroom - APC"},
	{"item_code": "Pie Tin", "qty": 60, "warehouse": "Storeroom - APC"},
	{"item_code": "Pie Box", "qty": 70, "warehouse": "Storeroom - APC"},
	{"item_code": "Sugar", "qty": 8, "warehouse": "Storeroom - APC"},
	{"item_code": "Salt", "qty": 1, "warehouse": "Storeroom - APC"},
	{"item_code": "Water", "qty": 15, "warehouse": "Kitchen - APC"},
	{"item_code": "Gooseberry", "qty": 30, "warehouse": "Refrigerator - APC"},
	{"item_code": "Cocoplum", "qty": 45, "warehouse": "Refrigerator - APC"},
	{"item_code": "Damson Plum", "qty": 45, "warehouse": "Refrigerator - APC"},
	{"item_code": "Bilberry", "qty": 53, "warehouse": "Refrigerator - APC"},
	{"item_code": "Kepel", "qty": 37, "warehouse": "Refrigerator - APC"},
	{"item_code": "Lime", "qty": 74, "warehouse": "Refrigerator - APC"},
	{"item_code": "Boquila", "qty": 74, "warehouse": "Refrigerator - APC"},
	{"item_code": "Bael", "qty": 83, "warehouse": "Refrigerator - APC"},
	{"item_code": "Highbush Cranberry", "qty": 17, "warehouse": "Refrigerator - APC"},
	{"item_code": "Sambucus", "qty": 85, "warehouse": "Refrigerator - APC"},
	{"item_code": "Redcurrant", "qty": 78, "warehouse": "Refrigerator - APC"},
	{"item_code": "Gac", "qty": 73, "warehouse": "Refrigerator - APC"},
	{"item_code": "European Blueberry", "qty": 1, "warehouse": "Refrigerator - APC"},
	{"item_code": "Giant Granadilla", "qty": 51, "warehouse": "Refrigerator - APC"},
	{"item_code": "Bearberry", "qty": 45, "warehouse": "Refrigerator - APC"},
	{"item_code": "Seedless Watermelon", "qty": 77, "warehouse": "Refrigerator - APC"},
	{"item_code": "Mini Watermelon", "qty": 4, "warehouse": "Refrigerator - APC"},
	{"item_code": "Kandis", "qty": 62, "warehouse": "Refrigerator - APC"},
	{"item_code": "Berberis Vulgaris", "qty": 65, "warehouse": "Refrigerator - APC"},
	{"item_code": "Blue Tongue", "qty": 32, "warehouse": "Refrigerator - APC"},
	{"item_code": "Kahikatea", "qty": 34, "warehouse": "Refrigerator - APC"},
	{"item_code": "Kabosu", "qty": 92, "warehouse": "Refrigerator - APC"},
	{"item_code": "Kaffir Lime", "qty": 95, "warehouse": "Refrigerator - APC"},
	{"item_code": "Black Apple", "qty": 72, "warehouse": "Refrigerator - APC"},
	{"item_code": "Black Cherry", "qty": 39, "warehouse": "Refrigerator - APC"},
	{"item_code": "Lychee", "qty": 26, "warehouse": "Refrigerator - APC"},
	{"item_code": "Jostaberry", "qty": 34, "warehouse": "Refrigerator - APC"},
	{"item_code": "Camu Camu", "qty": 54, "warehouse": "Refrigerator - APC"},
	{"item_code": "Batuan", "qty": 3, "warehouse": "Refrigerator - APC"},
	{"item_code": "Calamondin", "qty": 50, "warehouse": "Refrigerator - APC"},
	{"item_code": "Citron", "qty": 12, "warehouse": "Refrigerator - APC"},
	{"item_code": "Coco Plum", "qty": 65, "warehouse": "Refrigerator - APC"},
	{"item_code": "Horned Melon", "qty": 54, "warehouse": "Refrigerator - APC"},
	{"item_code": "Fragaria", "qty": 5, "warehouse": "Refrigerator - APC"},
	{"item_code": "Boysenberry", "qty": 94, "warehouse": "Refrigerator - APC"},
	{"item_code": "Chokeberry", "qty": 94, "warehouse": "Refrigerator - APC"},
	{"item_code": "Raisin", "qty": 57, "warehouse": "Refrigerator - APC"},
	{"item_code": "Lawton Blackberry", "qty": 17, "warehouse": "Refrigerator - APC"},
	{"item_code": "Cranberry", "qty": 47, "warehouse": "Refrigerator - APC"},
	{"item_code": "Bilimbi", "qty": 23, "warehouse": "Refrigerator - APC"},
	{"item_code": "Barbados Cherry", "qty": 79, "warehouse": "Refrigerator - APC"},
	{"item_code": "Photinia", "qty": 85, "warehouse": "Refrigerator - APC"},
	{"item_code": "Doubah", "qty": 14, "warehouse": "Refrigerator - APC"},
	{"item_code": "Coffee", "qty": 66, "warehouse": "Refrigerator - APC"},
	{"item_code": "Youngberry", "qty": 75, "warehouse": "Refrigerator - APC"},
	{"item_code": "Bacuri", "qty": 51, "warehouse": "Refrigerator - APC"},
	{"item_code": "Louvi", "qty": 38, "warehouse": "Refrigerator - APC"},
	{"item_code": "Jaltomata Procumbens", "qty": 64, "warehouse": "Refrigerator - APC"},
	{"item_code": "Empetrum", "qty": 98, "warehouse": "Refrigerator - APC"},
	{"item_code": "European Raspberry", "qty": 38, "warehouse": "Refrigerator - APC"},
	{"item_code": "Black Raspberry", "qty": 50, "warehouse": "Refrigerator - APC"},
	{"item_code": "Cryptocarya Alba", "qty": 98, "warehouse": "Refrigerator - APC"},
	{"item_code": "Canary Melon", "qty": 82, "warehouse": "Refrigerator - APC"},
	{"item_code": "Biriba", "qty": 30, "warehouse": "Refrigerator - APC"},
	{"item_code": "Cocky Apple", "qty": 79, "warehouse": "Refrigerator - APC"},
	{"item_code": "Edible Honeysuckle", "qty": 91, "warehouse": "Refrigerator - APC"},
	{"item_code": "Whinberry", "qty": 51, "warehouse": "Refrigerator - APC"},
	{"item_code": "Desert Lime", "qty": 63, "warehouse": "Refrigerator - APC"},
	{"item_code": "Myrciaria Floribunda", "qty": 98, "warehouse": "Refrigerator - APC"},
	{"item_code": "Physalis", "qty": 52, "warehouse": "Refrigerator - APC"},
	{"item_code": "Bitter Melon", "qty": 38, "warehouse": "Refrigerator - APC"},
	{"item_code": "Dabai", "qty": 97, "warehouse": "Refrigerator - APC"},
	{"item_code": "Beach Plum", "qty": 88, "warehouse": "Refrigerator - APC"},
	{"item_code": "Melon Pear", "qty": 79, "warehouse": "Refrigerator - APC"},
	{"item_code": "Blood Orange", "qty": 30, "warehouse": "Refrigerator - APC"},
	{"item_code": "Banana", "qty": 51, "warehouse": "Refrigerator - APC"},
	{"item_code": "Loquat", "qty": 81, "warehouse": "Refrigerator - APC"},
	{"item_code": "Eugenia Uniflora", "qty": 5, "warehouse": "Refrigerator - APC"},
	{"item_code": "Kakadu Lime", "qty": 29, "warehouse": "Refrigerator - APC"},
	{"item_code": "Karonda", "qty": 4, "warehouse": "Refrigerator - APC"},
	{"item_code": "Hippophae", "qty": 10, "warehouse": "Refrigerator - APC"},
	{"item_code": "Guava", "qty": 56, "warehouse": "Refrigerator - APC"},
	{"item_code": "Candlenut", "qty": 17, "warehouse": "Refrigerator - APC"},
	{"item_code": "Tomatillo", "qty": 74, "warehouse": "Refrigerator - APC"},
	{"item_code": "Olallieberry", "qty": 17, "warehouse": "Refrigerator - APC"},
	{"item_code": "Date", "qty": 84, "warehouse": "Refrigerator - APC"},
	{"item_code": "Midyim", "qty": 88, "warehouse": "Refrigerator - APC"},
	{"item_code": "Cowberry", "qty": 69, "warehouse": "Refrigerator - APC"},
	{"item_code": "Kapok", "qty": 34, "warehouse": "Refrigerator - APC"},
	{"item_code": "Durian", "qty": 6, "warehouse": "Refrigerator - APC"},
	{"item_code": "Desert Banana", "qty": 53, "warehouse": "Refrigerator - APC"},
	{"item_code": "Coconut", "qty": 66, "warehouse": "Refrigerator - APC"},
	{"item_code": "Triphasia Brassii", "qty": 77, "warehouse": "Refrigerator - APC"},
	{"item_code": "Kiwifruit", "qty": 43, "warehouse": "Refrigerator - APC"},
	{"item_code": "Hackberry", "qty": 75, "warehouse": "Refrigerator - APC"},
	{"item_code": "Genip", "qty": 23, "warehouse": "Refrigerator - APC"},
	{"item_code": "Goji", "qty": 55, "warehouse": "Refrigerator - APC"},
	{"item_code": "Clementine", "qty": 80, "warehouse": "Refrigerator - APC"},
	{"item_code": "Huckleberry", "qty": 95, "warehouse": "Refrigerator - APC"},
	{"item_code": "Sultana", "qty": 75, "warehouse": "Refrigerator - APC"},
	{"item_code": "Bacupari", "qty": 16, "warehouse": "Refrigerator - APC"},
	{"item_code": "White Currant", "qty": 8, "warehouse": "Refrigerator - APC"},
	{"item_code": "Raspberry", "qty": 4, "warehouse": "Refrigerator - APC"},
]
>>>>>>> d1de7e2 (split by time for LIFO/FIFO)
