"""Frictionless Data datapackage.json related functions

See http://specs.frictionlessdata.io/data-package/ for datapackage specs
"""
import re
from typing import Any, Dict

import frictionless_ckan_mapper.ckan_to_frictionless as ctf
import frictionless_ckan_mapper.frictionless_to_ckan as ftc
from six import iteritems

FALLBACK_RESOURCE_PATH = 'resource'


def dataset_to_frictionless(ckan_dataset):
    """Convert a CKAN dataset dict to a Frictionless datapackage
    """
    package = _convert_excluding_path(ckan_dataset)
    _normalize_resource_paths(package)
    return package


def frictionless_to_dataset(datapackage):
    """Convert a Frictionless data datapackage dict to a CKAN dataset dict
    """
    return ftc.package(datapackage)


def _convert_excluding_path(ckan_dataset):
    """Convert a CKAN dataset to a frictionless package but exclude custom `path` values

    This is done because frictionless_ckan_mapper will override `path` if URL is set for
    a resource, but we want to preserve `path` if it was previously set.
    """
    existing_paths = {i: r['path']
                      for i, r in enumerate(ckan_dataset.get('resources', []))
                      if 'path' in r}

    package = ctf.dataset(ckan_dataset)

    for i, path in iteritems(existing_paths):
        package['resources'][i]['path'] = path

    return package


def _normalize_resource_paths(package):
    """Normalize the paths of all resources
    """
    parent_dir_re = re.compile(r'/?(?:(?:\.)+/)+')
    existing_paths = set()

    for counter, resource in enumerate(package.get('resources', [])):
        path = _get_resource_path(resource)
        if path is None:
            continue

        path = parent_dir_re.sub('/', path)
        try:
            while path[0] == '/':
                path = path[1:]
        except IndexError:
            path = FALLBACK_RESOURCE_PATH

        if path in existing_paths:
            path = _add_filename_suffix(path, '-{}'.format(counter))
        else:
            existing_paths.add(path)

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
        path = None
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


def update_ckan_dict(ckan_dict, dataset):
    """ Updates the CKAN package dict with metadata from metastore.
    """
    ckan_dict.update(dataset)
    if len(ckan_dict.get('extras', [])) > 0:
        ckan_dict['extras'] = _normalize_extras(ckan_dict)
    for resource in ckan_dict.get('resources'):
        resource['package_id'] = ckan_dict.get('id')
    return ckan_dict


def _normalize_extras(ckan_dict):
    """Normalize extras returned by frictionless-ckan-mapper

    This removes any extras item that already exists in the main CKAN package dict,
    because we know this will not pass validation
    """
    return [e for e in ckan_dict['extras'] if e['key'] not in ckan_dict]
