"""Frictionless Data datapackage.json related functions

See http://specs.frictionlessdata.io/data-package/ for datapackage specs
"""
import re
from typing import Any, Dict

from ckan_datapackage_tools import converter

FALLBACK_RESOURCE_PATH = 'resource'


def dataset_to_frictionless(package):
    """Convert a CKAN dataset dict to a Frictionless datapackage
    """
    dp = converter.dataset_to_datapackage(package)
    _normalize_resource_paths(dp)
    return dp


def frictionless_to_dataset(package):
    """Convert a Frictionless data datapackage dict to a CKAN dataset dict
    """
    return converter.datapackage_to_dataset(package)


def _normalize_resource_paths(package):
    """Normalize the paths of all resources
    """
    parent_dir_re = re.compile(r'(?:/?\.\./|/\./)+')
    existing_paths = set()

    for counter, resource in enumerate(package['resources']):
        path = _get_resource_path(resource)

        path = parent_dir_re.sub('/', path)
        try:
            while path[0] == '/':
                path = path[1:]
        except IndexError:
            path = FALLBACK_RESOURCE_PATH

        if path in existing_paths:
            path = _add_filename_suffix(path, '-{}'.format(counter))

        resource['path'] = path


def _get_resource_path(resource):
    # type: (Dict[str, Any]) -> str
    """Get the `path` value for a resource

    Apply the following rules in order

    Generate an initial value for path:
        If a path variable exists, use it. END
        If url exists, use it. END
        If sha256 is set use the name and format: {NAME-LOWER-CASE}.{FORMAT}

    If path contains /../ or begins with /, normalize by striping any leading / and replacing any /../ with -.

    Ensure generated path does not conflict with other path values in the same datapackage:
        If it conflicts use suffixes based on position in resource list
        e.g. "{NAME}-{POS}.{FORMAT}"

    """

    if 'path' in resource:
        path = resource['path']
    elif 'url' in resource:
        path = resource.pop('url')
    elif 'sha256' in resource and 'name' in resource and 'format' in resource:
        path = '{name}.{format}'.format(name=resource['name'], format=resource['format']).lower()
    else:
        path = FALLBACK_RESOURCE_PATH
    return path


def _add_filename_suffix(original, suffix):
    # type: (str, str) -> str
    """Add a suffix to a filename
    """
    parts = original.rsplit('.', 1)
    filename = '{}{}'.format(parts[0], suffix)
    if len(parts) > 1:
        filename += '.{}'.format(parts[1])
    return filename
