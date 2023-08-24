# CHANGELOG



## v14.1.0 (2023-08-24)

### Chore

* chore: update test data for erpnext codebase changes (#24) ([`b7dfc02`](https://github.com/agritheory/inventory_tools/commit/b7dfc02e228c4ebdca86000dac65d1a903640b15))

### Ci

* ci: update remote name ([`021b8a4`](https://github.com/agritheory/inventory_tools/commit/021b8a47355cb9028bac7ac8e60d224247d5b0e8))

* ci: update version number ([`9d82150`](https://github.com/agritheory/inventory_tools/commit/9d821506af9d6eb72e3bfb1345ac652aa86896dc))

* ci: add python semantic release ([`703803d`](https://github.com/agritheory/inventory_tools/commit/703803df7949fb0cb43699482425ec31595dd1b9))

### Documentation

* docs: update material demand section for expanded functionality ([`1af88f6`](https://github.com/agritheory/inventory_tools/commit/1af88f6d06fdc8e6908381f9dd9011fe470dd9d7))

### Feature

* feat: select email template ([`02196e3`](https://github.com/agritheory/inventory_tools/commit/02196e37c7234982c5dafda9e814117d374565a9))

### Fix

* fix: blank email template for PO; skip supplier-only rows for RFQ ([`2a0e8cd`](https://github.com/agritheory/inventory_tools/commit/2a0e8cd6c6aefdd1a0d7b978652f97ddc755523f))

* fix: fix JS after adding draft PO column (#26) ([`e0d3229`](https://github.com/agritheory/inventory_tools/commit/e0d322950e87dcf09f13441859e273a0e44a1192))

### Unknown

* Merge pull request #23 from agritheory/issue_19

Allow Creation of RFQ from Material Demand report ([`8a0e350`](https://github.com/agritheory/inventory_tools/commit/8a0e35024968ce5a0f6da05e71f62c091bf2b38f))

* Work Order Subcontracting (#13)

* tests: update test data for additional manufacturing workflow

* feat: work order subcontracting validations

* tests: add valuation rate for subcontracted item

* feat: start wo subcontracting feat

* feat: make subcontracting section visible by check and settings

* feat: add ste detail paid field and new pi cols

* feat: setup hooks and custom po

* tests: update data for default supplier and price lists

* feat: include doctype js

* feat: add work order customizations

* feat: add purchase order customizations

* feat: update purchase invoice customizations

* feat: remove unused code blocks

* fix: add module to json

* fix: update custom doc path

* feat: consolidate custom PI code and modularize class functions

* feat: combine and refactor PO code

* feat: update server function paths

* feat: add BOM field default

* feat: update to use BOM field vs Item for is_subcontracted

* feat: code cleanup and refactoring for BOM field

* feat: update for uom conversion and new svc item

* fix: move UOM conversions to item

* add todos in JS

* feat: rewire item adjustments for conversion factor

* wip: integrate with production plan

* feat: add supplier field in WO, allow selection of supplier in dialog

* chore: add comment explaining precision code

* wip: subcontractor workflow

* feat: subcontracting workflow with correct warehouses

* feat: show/hide subcontracting columns

* feat: colorize fetach stock entries button

* fix: text artifacts, new PO errors

* feat: fetch supplier warehouse, added connectiosn to PI and PO from WO

* feat: add filters and looks to both PI and PO

* fix: monkey patch validate_item_details

* feat: remove buttons and update stockfield in WO subc workflow

* Enforce UOMs to those that exist in the Item&#39;s conversion detail (#27)

* wip: uom restricted query

* feat: refactor UOM enforcement validation to be hookable

* docs: add docs for UOM enforcement

* tests: fix test logger problem, add xfail uom test

* Warehouse path (#25)

* wip: warehouse path

* wip: warehouse path

* wip: warehouse path feature

* feat: warehouse path builder

* feat: undo query when not configured; setup tweaks

* chore: update test data for erpnext codebase changes (#24)

* wip: warehouse path feature

* wip: test setup

* chore: update yarn

* tests: trying to defaeat logger problem

* test: fix conftest logger issue

* docs: add docs for warehouse path

* chore: union types for whitelisted function

---------

Co-authored-by: Heather Kusmierz &lt;heather.kusmierz@gmail.com&gt;

* tests: test cadence (#28)

* fix: no cancelled PO in se query, code clean up

* chore: add comment to explain monkey patch rationale

---------

Co-authored-by: Tyler Matteson &lt;tyler@agritheory.com&gt; ([`ac11c1d`](https://github.com/agritheory/inventory_tools/commit/ac11c1df4daad2189916ca9841480aa1796e42e3))

* Merge branch &#39;version-14&#39; into issue_19 ([`ee0a27f`](https://github.com/agritheory/inventory_tools/commit/ee0a27f0f03a8e3c9e9fa54011d02e44554b8bbb))

* Documentation (#29)

* docs: add index page

* docs: add screen shots and workflow

* docs: add screen shots, text edits

* docs: add example data page

* docs: add placeholder pages

* docs: add subcontracting via WO section

* docs: edits, conform text conventions ([`2fc980d`](https://github.com/agritheory/inventory_tools/commit/2fc980d41105759cffa33e610b779b6d464cf24c))

* tests: test cadence (#28) ([`6b5bd47`](https://github.com/agritheory/inventory_tools/commit/6b5bd47089fb2f8a09159635e618425743cc9dff))

* Warehouse path (#25)

* wip: warehouse path

* wip: warehouse path

* wip: warehouse path feature

* feat: warehouse path builder

* feat: undo query when not configured; setup tweaks

* chore: update test data for erpnext codebase changes (#24)

* wip: warehouse path feature

* wip: test setup

* chore: update yarn

* tests: trying to defaeat logger problem

* test: fix conftest logger issue

* docs: add docs for warehouse path

* chore: union types for whitelisted function

---------

Co-authored-by: Heather Kusmierz &lt;heather.kusmierz@gmail.com&gt; ([`370dd6f`](https://github.com/agritheory/inventory_tools/commit/370dd6f9789156ebcbbe7b111d891a74731a477b))

* Enforce UOMs to those that exist in the Item&#39;s conversion detail (#27)

* wip: uom restricted query

* feat: refactor UOM enforcement validation to be hookable

* docs: add docs for UOM enforcement

* tests: fix test logger problem, add xfail uom test ([`d4c145a`](https://github.com/agritheory/inventory_tools/commit/d4c145a94d8402fa441619289b4cc6438b7d5c45))

* Documentation (#29)

* docs: add index page

* docs: add screen shots and workflow

* docs: add screen shots, text edits

* docs: add example data page

* docs: add placeholder pages

* docs: add subcontracting via WO section

* docs: edits, conform text conventions ([`198e110`](https://github.com/agritheory/inventory_tools/commit/198e110ab0c5461b9c46925fc05af351151abd38))

* tests: test cadence (#28) ([`b91e024`](https://github.com/agritheory/inventory_tools/commit/b91e0246f6e384f40685af40d3a249daa9d03a8c))

* Warehouse path (#25)

* wip: warehouse path

* wip: warehouse path

* wip: warehouse path feature

* feat: warehouse path builder

* feat: undo query when not configured; setup tweaks

* chore: update test data for erpnext codebase changes (#24)

* wip: warehouse path feature

* wip: test setup

* chore: update yarn

* tests: trying to defaeat logger problem

* test: fix conftest logger issue

* docs: add docs for warehouse path

* chore: union types for whitelisted function

---------

Co-authored-by: Heather Kusmierz &lt;heather.kusmierz@gmail.com&gt; ([`e3fb9c7`](https://github.com/agritheory/inventory_tools/commit/e3fb9c7f2a8ed3c42f4cb47078086bcdd60f91c7))

* Enforce UOMs to those that exist in the Item&#39;s conversion detail (#27)

* wip: uom restricted query

* feat: refactor UOM enforcement validation to be hookable

* docs: add docs for UOM enforcement

* tests: fix test logger problem, add xfail uom test ([`65d42e1`](https://github.com/agritheory/inventory_tools/commit/65d42e126d81f3ed1b98178f7b6c68c6a070986e))


## v14.0.1 (2023-08-10)

### Chore

* chore: update test data for erpnext codebase changes (#24) ([`48160aa`](https://github.com/agritheory/inventory_tools/commit/48160aa27f5d0deb3be5e6e55f16d35fd92ae086))

### Ci

* ci: update remote name ([`218eb06`](https://github.com/agritheory/inventory_tools/commit/218eb06a6a4a2ac3f5b9ee214a130e2c8ba30d29))

* ci: update version number ([`6e0c194`](https://github.com/agritheory/inventory_tools/commit/6e0c194235a19011b0c7db5adb8ed7e5954ba5eb))

* ci: add python semantic release ([`3382787`](https://github.com/agritheory/inventory_tools/commit/3382787d4726d7483a7243eafff03eb775d0ac3e))

### Feature

* feat: based on item option ([`cc90229`](https://github.com/agritheory/inventory_tools/commit/cc90229b9ccf27cb5a872b24109dc7071f146802))

* feat: wip, make rfqs ([`c5a8867`](https://github.com/agritheory/inventory_tools/commit/c5a88673c3d57480a10ec68091e04a75488e18cb))

* feat: wip material demand options ([`bedd3d4`](https://github.com/agritheory/inventory_tools/commit/bedd3d42f299c73c1c1fa80c3a4928316d1428a2))

* feat: requires_rfq custom field, creation options in report ([`cd4ec42`](https://github.com/agritheory/inventory_tools/commit/cd4ec42e15fdbfa2cc24dc41b16562e74daf6124))

### Fix

* fix: fix JS after adding draft PO column (#26) ([`42aefa9`](https://github.com/agritheory/inventory_tools/commit/42aefa9abab60962f923870a151d7bacbceba141))

### Unknown

* Merge pull request #22 from agritheory/ci_fix

ci: update remote name ([`946657b`](https://github.com/agritheory/inventory_tools/commit/946657b179d2a8ba6934c2df7ca5d83f9bb04f29))

* Merge pull request #21 from agritheory/py_sem_rel_14

ci: add python semantic release ([`13b41fa`](https://github.com/agritheory/inventory_tools/commit/13b41fad052f9c45e017b6fbac6897bdf38b7883))


## v14.0.0 (2023-07-21)

### Documentation

* docs: wip material demand docs ([`6116a1b`](https://github.com/agritheory/inventory_tools/commit/6116a1b30b77565ff0470af32f8f59aa7a949786))

### Feature

* feat: add column for draft PO amount ([`59d837b`](https://github.com/agritheory/inventory_tools/commit/59d837b1d3dbf4798d08618d033f732cad76cf1f))

* feat: create inventory tools settings when company is created ([`0121499`](https://github.com/agritheory/inventory_tools/commit/0121499bd99fa9ff5126b7432dd1d9a1d2816dd4))

* feat: create inventory tools settings when company is created ([`edff215`](https://github.com/agritheory/inventory_tools/commit/edff215f58ce8163da37436af893e1395164520c))

* feat: material demand PO creation ([`794f735`](https://github.com/agritheory/inventory_tools/commit/794f7352b27eb000ca96ece71c8081b69f519751))

* feat: add setting doctype ([`25a75de`](https://github.com/agritheory/inventory_tools/commit/25a75de2f1415ed78634d45c255438f1ed7a3ad1))

* feat: Initialize App ([`9e932fe`](https://github.com/agritheory/inventory_tools/commit/9e932fe49e70d5f2507d5900839c32f063a20898))

### Fix

* fix: purchase order custom filed missing, carry price list from report to PO ([`4fe5ac8`](https://github.com/agritheory/inventory_tools/commit/4fe5ac84f52d656db3017af5e5a2a08111b2a729))

* fix: add back price list filter, fix schema ([`ceda857`](https://github.com/agritheory/inventory_tools/commit/ceda85797cc62a2d0e70e3a1135a88492f5c2cc0))

* fix: rebased v14 conflicts ([`b1614cb`](https://github.com/agritheory/inventory_tools/commit/b1614cb28a3f57d31c2056bf4e4506fd94a6e997))

* fix: supplier level de-selection and filtering ([`94140d0`](https://github.com/agritheory/inventory_tools/commit/94140d042a2e3fec79a56f0cacb86725dc2539b7))

* fix: module import name ([`ae290f8`](https://github.com/agritheory/inventory_tools/commit/ae290f8a392d9c5b3ea941244e68c8f1099728ef))

### Unknown

* Merge pull request #20 from agritheory/material_demand

Material Demand report fixes ([`7eb3c87`](https://github.com/agritheory/inventory_tools/commit/7eb3c877932a4d072ff56af23ad77958aba2fc36))

* Merge pull request #15 from agritheory/material_demand

Material Demand ([`486fde6`](https://github.com/agritheory/inventory_tools/commit/486fde69cfdfa8810d93445ef4b32eb0753e799c))

* Merge branch &#39;version-14&#39; into material_demand ([`9275dbf`](https://github.com/agritheory/inventory_tools/commit/9275dbf04f30a7391a0c003fff77cc5b105bd4cb))

* wip: material demand report improvements ([`d167804`](https://github.com/agritheory/inventory_tools/commit/d167804e90e10fc8299a49f6f0b90a512e93b5a3))

* wip: material demand ([`067b0d7`](https://github.com/agritheory/inventory_tools/commit/067b0d71dc372c35ac988556b20d13b9ab95f009))

* Merge pull request #16 from agritheory/settings_hook

feat: create inventory tools settings when company is created ([`acc2b9c`](https://github.com/agritheory/inventory_tools/commit/acc2b9c640e1cb9eadf2e96060518a323ce34990))

* wip: material demand

selection helpers look good except for supplier-level deselect, which toggles everything backwards ([`de7e09c`](https://github.com/agritheory/inventory_tools/commit/de7e09c4e04456fcd5d23fdbfa30c3a8a1933c28))

* wip: warehouse path ([`3ef9d3e`](https://github.com/agritheory/inventory_tools/commit/3ef9d3e7a30a98339f7d09c5ecba2e666e877b49))

* wip: material demand report improvements ([`c20379a`](https://github.com/agritheory/inventory_tools/commit/c20379aae9659fc1280f3c884bc888cce765116d))

* wip: material demand ([`3f50d5f`](https://github.com/agritheory/inventory_tools/commit/3f50d5f96b5b0a57993320e4f3c56034a490cd9a))

* wip: material demand ([`0cb8694`](https://github.com/agritheory/inventory_tools/commit/0cb869487fc576470f5ddb7f1b8f3b23f4cc1a57))

* Merge pull request #7 from agritheory/settings_doctype

feat: add setting doctype ([`5285a99`](https://github.com/agritheory/inventory_tools/commit/5285a9967fc3615f16c7d4b06ac6f55589966975))

* Merge pull request #6 from agritheory/test_data_fixes

fix: module import name ([`6edf7fb`](https://github.com/agritheory/inventory_tools/commit/6edf7fb0127648c90b0e3c203473681b8b964b63))

* initial commit ([`a09e1ed`](https://github.com/agritheory/inventory_tools/commit/a09e1ed6724ea49e39d5e208e6031283bf282f97))
