# Using the Example Data to Experiment with Inventory Tools

The Inventory Tools application comes with a `setup.py` script that is completely optional to use. If you execute the script, it populates an ERPNext site with demo business data for a fictitious company called Ambrosia Pie Company. The data enable you to experiment and test the Inventory Tools application's functionality before installing the app into your ERPNext site.

It's recommended to install the demo data into its own site to avoid potential interference with the configuration or data in your organization's ERPNext site.

With `bench start` running in the background, run the following command to install the demo data:

```shell
bench execute 'inventory_tools.tests.setup.before_test'
# to reinstall from scratch and set up test data
bench reinstall --yes --admin-password admin --mariadb-root-password admin && bench execute 'inventory_tools.tests.setup.before_test'
```

Refer to the [application repository](https://github.com/agritheory/inventory_tools) for detailed instructions for how to set up a bench, a new site, and installing ERPNext and the Inventory Tools application.
