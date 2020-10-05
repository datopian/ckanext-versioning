# encoding: utf-8
from ckan.authz import is_authorized
from ckan.plugins import toolkit


def dataset_revert(context, data_dict):
    """Check if a user is allowed to revert a dataset to a release

    This is permitted only to users who are allowed to modify the dataset
    """
    return is_authorized('package_update', context,
                         {"id": data_dict['dataset']})


def dataset_release_create(context, data_dict):
    """Check if a user is allowed to create a release

    This is permitted only to users who are allowed to modify the dataset
    """
    return is_authorized('package_update', context,
                         {"id": data_dict['dataset']})


def dataset_release_delete(context, data_dict):
    """Check if a user is allowed to delete a release

    This is permitted only to users who are allowed to modify the dataset
    """
    return is_authorized('package_update', context,
                         {"id": data_dict['dataset']})


@toolkit.auth_allow_anonymous_access
def dataset_release_list(context, data_dict):
    """Check if a user is allowed to list dataset releases

    This is permitted only to users who can view the dataset
    """
    return is_authorized('package_show', context, {"id": data_dict['dataset']})


@toolkit.auth_allow_anonymous_access
def dataset_release_show(context, data_dict):
    """Check if a user is allowed to view dataset releases

    This is permitted only to users who can view the dataset
    """
    return is_authorized('package_show', context, {"id": data_dict['dataset']})


@toolkit.auth_allow_anonymous_access
def dataset_release_diff(context, data_dict):
    return dataset_release_show(context, data_dict)
