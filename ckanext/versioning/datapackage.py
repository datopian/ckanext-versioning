"""Frictionless Data datapackage.json related functions

See http://specs.frictionlessdata.io/data-package/ for datapackage specs
"""
from ckan_datapackage_tools import converter


def dataset_to_frictionless(package):
    """Convert a CKAN dataset dict to a Frictionless datapackage
    """
    return converter.dataset_to_datapackage(package)


def frictionless_to_dataset(package):
    """Convert a Frictionless data datapackage dict to a CKAN dataset dict
    """
    for resource in package['resources']:
        resource['path'] = _get_resource_path(resource)
    return converter.datapackage_to_dataset(package)


def _get_resource_path(resource):
    """Get the `path` value for a resource
    """
    return ''
