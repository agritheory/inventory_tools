from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in inventory_tools/__init__.py
from inventory_tools import __version__ as version

setup(
	name="inventory_tools",
	version=version,
	description="Inventory Tools",
	author="AgriTheory",
	author_email="support@agritheory.dev",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
