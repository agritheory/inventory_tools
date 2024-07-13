# CHANGELOG


## v14.6.0 (2024-05-13)

### Chore

* chore: update quotation demand docs (#77) ([`f168079`](https://github.com/agritheory/inventory_tools/commit/f168079e29d99056d4c5eb2321d84957cff84f3b))

### Feature

* feat: add inventory tools settings to boot (#81) ([`7ac2e15`](https://github.com/agritheory/inventory_tools/commit/7ac2e15aa74676ba5741887231814cdf9e675755))


## v14.5.0 (2024-04-29)

### Feature

* feat: allow user to bulk upload items with quantity to shopping cart (#70)

* feat: allow user to bulk upload items with quantity to shoping cart

* nit: variable and syntactical changes

* fix: removed line by line order placing, optimised code, added enqueue

* fix: minor cleanup

---------

Co-authored-by: Rohan Bansal &lt;rohan@agritheory.dev&gt; ([`748a9bc`](https://github.com/agritheory/inventory_tools/commit/748a9bc85034094dcd60544fe2b822b67322fb44))

### Unknown

* Aggregate and/or Split Quotations into multiple Sales Orders  (#65)

* feat: Quotation Demand

* feat: hook

* feat: settings for quotation demand

* feat: fixes, SO validate_warehouse

* feat: quotation demand tests

* feat: documentation

* feat: improvements

* feat: improve tests

* feat: total selected, price, draft so

* feat: tests ([`6eceeb5`](https://github.com/agritheory/inventory_tools/commit/6eceeb5623856d659db1ffc3dd7a3ce352cd8000))


## v14.4.0 (2024-04-25)

### Ci

* ci: add black to ci (#61)

* ci: add black to ci

* chore: black ([`db5a742`](https://github.com/agritheory/inventory_tools/commit/db5a7427f068d7005f8f07125d81f1430c49eb9b))

### Feature

* feat: aggregate POs (#71) ([`5ff8fee`](https://github.com/agritheory/inventory_tools/commit/5ff8fee2ef356990e2dcda0d2db76d1b856a0685))

### Unknown

* Material Demand Test (#64)

* wip: material demand tests

* test: material demand aggregation tests and fixes with and without warehouse

* test: material demand tests and bug fixes

* chore: add mypy types isntall

* fix: remove duplicate function

* tests: add pytest runner file

* tests: add helper files

* tests: correct app name

* ci: fix site_config

* ci: update action version to use node 20

* ci: hrms get-app

* ci: add base branch sensitvie get-app

* ci: add hrms to install

* ci: add node 20 versions

* ci: remove hrms from install-apps

* ci: get-app for hrms

* ci: update prettier and changed-files actions

* ci: ad dhrms to apps.txt

* ci: get-app for hrms again

* ci: get-app for hrms only

* ci: overrite erpnext install (hrms is tryign to install develop branch)

* ci: add app name

* ci: add repo to required apps

* ci: try install hrms first with overwrite

* ci: remove &#34;install_apps&#34; key from site_config

* ci: remove required apps

* feat: use query builder

* ci: remove resolve deps

* ci: fix install apps

* test: fix manufacturing capacity test and report

* test: cleanup uom test

* test: fix error message assert

* test: add ordering

* fix: test

* fix: use frappe function

* fix: use frappe function

---------

Co-authored-by: fproldan &lt;franciscoproldan@gmail.com&gt; ([`6f4f63f`](https://github.com/agritheory/inventory_tools/commit/6f4f63f22f3f7278e20c6aba9e5ef6a021ae03b2))

* Manufacturing capacity report (#57)

* ci: update app in str(file path) code to more exact matching

* chore: remove unused code

* feat: add manufacturing capacity report

* tests: start manufacturing capacity report tests

* chore: uncomment formatting code

* docs: add manufacturing capacity report documentation

* fix: div by zero in parts can build calc

* docs: update for calculation differences

* fix: in stock qty to zero if none from query ([`2936cde`](https://github.com/agritheory/inventory_tools/commit/2936cde9aac6583edeb383d94d74142461cf243a))


## v14.3.0 (2024-03-01)

### Feature

* feat: Alternative workstation in job card and operation (#56)

* feat: New field and link filters to select alternative workstation

* fix: add alternativ workstation in fixture

* fix:change alternative workstation in fixture

* change to error key function

* fix: set validation on workstation if not operation

* changes field name in testcase

* fix: change a class base function to saperate function

* added a searchfield in query

* added a searchfield in query

* added a searchfield in query

* added a searchfield in query

* added a searchfield in query

* feat: validation to not allow default workstation in alternative

* added comment on function ([`0788d3c`](https://github.com/agritheory/inventory_tools/commit/0788d3caa67ad7820a5a3cdfdc950c85bd6f0cd7))

### Unknown

* Prompt Material Transfer upon Completion of Manufacturing Stock Entry (#51)

* feat: wip stock entry next action

* feat: improve message

* fix: on_submit hook

* fix: parameter hardcoded

* feat: change wording ([`d1e126b`](https://github.com/agritheory/inventory_tools/commit/d1e126b8dbaf09370f6d4c173e24af33ac994bd7))


## v14.2.0 (2024-02-01)

### Feature

* feat: manufacturing over/under production

* feat: WIP Manufacturing Over/Under Production

* feat: WIP Manufacturing Over/Under Production

* feat: WIP Manufacturing Over/Under Production

* fix: unused import

* feat: override onload for work order

* feat: oveeride get_pending_raw_materials

* fix: allowed_qty in job card

* fix: indentation

* fix: import

* fixes

* wip: tests

* feat: test_get_allowance_percentage

* feat: test test_validate_finished_goods

* fix: validate_job_card and test

* fix: test ([`baeb469`](https://github.com/agritheory/inventory_tools/commit/baeb4690d42429a062595eb9058ddd2770b190c9))

### Unknown

* Make Creation of Job Card(s) on Submit of Work Order configurable (#49)

* feat: configurable creation of job card

* feat: configurable creation of job card ([`5bf9486`](https://github.com/agritheory/inventory_tools/commit/5bf94860c58d81faccb1106828f16121c081871a))


## v14.1.3 (2024-01-04)

### Fix

* fix: validate customizations (#35)

* fix: validate customizations

* fix: only install inventory tools customizations ([`e1d86a0`](https://github.com/agritheory/inventory_tools/commit/e1d86a0739e56f3b987b599c275644ee5c29fc0a))


## v14.1.2 (2023-09-12)

### Chore

* chore: remove console.log ([`f82b590`](https://github.com/agritheory/inventory_tools/commit/f82b590d061608818170092f07e3da8d9153b756))

### Ci

* ci: update release action user and email (#32) ([`4264bdd`](https://github.com/agritheory/inventory_tools/commit/4264bdde25c0bff1390923e7f18fce7c353844db))

### Fix

* fix: make uom enforcement respond better to toggle on/off ([`3734cb4`](https://github.com/agritheory/inventory_tools/commit/3734cb42e880168bb4c4a71c67820da63857e0bf))

### Unknown

* Merge pull request #33 from agritheory/uom_enforcement_fix

fix: make uom enforcement respond better to toggle on/off ([`13ad883`](https://github.com/agritheory/inventory_tools/commit/13ad8832a346799563e0f7ae2f1b20c457d10d5c))


## v14.1.1 (2023-08-30)

### Fix

* fix: add is_subcontracted check for additional validation/submit/cancel code ([`8182dac`](https://github.com/agritheory/inventory_tools/commit/8182dacfd35d2a2ee4c5ee94211cbfc7ac00abfd))

### Unknown

* Merge pull request #30 from agritheory/fix_subc_validation

fix: add is_subcontracted check for additional validation/submit/cancel code ([`c4e7b83`](https://github.com/agritheory/inventory_tools/commit/c4e7b83fd1700d08e8f711e10f1a77c81da0de32))


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

