"""Frictionless Data datapackage.json related functions

See http://specs.frictionlessdata.io/data-package/ for datapackage specs
"""
import frictionless_ckan_mapper.ckan_to_frictionless as ctf
import frictionless_ckan_mapper.frictionless_to_ckan as ftc


def dataset_to_frictionless(package):
    """Convert a CKAN dataset dict to a Frictionless datapackage
    """
    # TODO: Use ckan_mapper
    # return ctf.dataset(package)
    return package


def frictionless_to_dataset(package):
    """Convert a Frictionless data datapackage dict to a CKAN dataset dict
    """
    # TODO: Use ckan_mapper
    # return ftc.package(package)
    return package


def update_ckan_dict(ckan_dict, dataset):
    """ Updates the CKAN package dict with metadata from metastore.
    """
    ckan_dict.update(dataset)
    return ckan_dict
