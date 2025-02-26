<!-- Copyright (c) 2024, AgriTheory and contributors
For license information, please see license.txt-->

## Inventory Tools

Inventory Tools for ERPNext

#### License

MIT

## Install Instructions

Set up a new bench, substitute a path to the python version to use, which should 3.10 latest

```
# for linux development
bench init --frappe-branch version-15 {{ bench name }} --python ~/.pyenv/versions/3.10.16/bin/python3
```
Create a new site in that bench
```
cd {{ bench name }}
bench new-site {{ site name }} --force --db-name {{ site name }}
bench use {{ site name }}
```
Download the ERPNext app, other dependencies, and this application
```
bench get-app erpnext --branch version-15
bench get-app hrms --branch version-15
bench get-app payments --branch version-15
bench get-app webshop --branch version-15
bench get-app inventory_tools --branch version-15 git@github.com:agritheory/inventory_tools.git
```
Install all apps into the site
```
bench install-app erpnext hrms payments webshop inventory_tools
```
Set developer mode in `site_config.json`
```
cd {{ site name }}
nano site_config.json

 "developer_mode": 1,
```

Update and get the site ready
```
bench start
```
In a new terminal window
```
bench update
bench migrate
bench build
```

Setup test data
```shell
bench execute 'inventory_tools.tests.setup.before_test'
# for complete reset to run before tests:
bench reinstall --yes --admin-password admin --mariadb-root-password admin && bench execute 'inventory_tools.tests.setup.before_test'
```

To run mypy
```shell
source env/bin/activate
mypy ./apps/inventory_tools/inventory_tools --ignore-missing-imports
```

To run pytest
```shell
source env/bin/activate
pytest ./apps/inventory_tools/inventory_tools/tests -s
```
