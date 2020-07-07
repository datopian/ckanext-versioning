from ckan import model
from ckan.plugins import toolkit

from ckanext.versioning.common import get_metastore_backend
from ckanext.versioning.lib.changes import check_metadata_changes, check_resource_changes
from ckanext.versioning.model import DatasetVersion


def url_for_version(package, version=None, **kwargs):
    """Get the URL for a package / resource related action, with potential
    revision ID taken from a version info object

    If `version` is set, the version ID is appended to the package ID,
    and a ?version=... query parameter is added to URLs.

    If the `resource_id` parameter is provided and `version` is set, a
    revision ID will be appended to the resource_id.

    If the `route_name` parameter is provided, it will be used as the route
    name; Otherwise, `controller` and `action` are expected as arguments.
    """
    if version:
        kwargs['revision_ref'] = version['package_revision_id']
    kwargs['package_id'] = package.get('name', package['id'])

    if 'route_name' in kwargs:
        route = kwargs.pop('route_name')
        return toolkit.url_for(route, **kwargs)
    else:
        return toolkit.url_for(**kwargs)


def url_for_resource_version(package, version, **kwargs):
    """Similar to `url_for_version`, but also adds an "@revision" to the
    resource_id if it and a version is provided

    :param package:
    :param version:
    :param kwargs:
    :return:
    """
    if version and 'resource_id' in kwargs:
        kwargs['resource_id'] = "@".join([kwargs['resource_id'],
                                          version['package_revision_id']])

    return url_for_version(package, version, **kwargs)


def has_link_resources(package):
    """Return True if any resource in the dataset is a link to an external
    resource.
    """
    link_resource = any(
        resource['url_type'] is None or resource['url_type'] == ''
        for resource in package.get('resources', [])
    )

    return link_resource


def compare_pkg_dicts(old, new, old_activity_id):
    '''
    Takes two package dictionaries that represent consecutive versions of
    the same dataset and returns a list of detailed & formatted summaries of
    the changes between the two versions. Old and new are the two package
    dictionaries. The function assumes that both dictionaries will have
    all of the default package dictionary keys, and also checks for fields
    added by extensions and extra fields added by the user in the web
    interface.

    Returns a list of dictionaries, each of which corresponds to a change
    to the dataset made in this revision. The dictionaries each contain a
    string indicating the type of change made as well as other data necessary
    to form a detailed summary of the change.
    '''
    change_list = []

    check_metadata_changes(change_list, old, new)

    check_resource_changes(change_list, old, new, old_activity_id)

    # if the dataset was updated but none of the fields we check were changed,
    # display a message stating that
    if len(change_list) == 0:
        change_list.append({u'type': 'no_change'})

    return change_list


def get_license(license_id):
    '''
    Get the license details from the license_id as license details are
    not stored in DB but in the license file.
    Method package_show doesn't fetch the license again from file but
    only from SOLR. So need to fetch the license details in case of versions
    from the license file.
    Using the upsteam method to fetch license Details
    https://github.com/ckan/ckan/blob/8f271bfe3eccaa83a419ee55e3e35042d1196c5a/ckan/logic/action/get.py#L1806
    '''

    return model.Package.get_license_register().get(license_id)


def get_dataset_revision_list(dataset_name):
    '''List all revisions in metastore-lib for the given dataset.

    '''
    backend = get_metastore_backend()

    return [rev.revision for rev in backend.revision_list(dataset_name)]


def get_dataset_current_revision(dataset_name):
    '''Get the current revision in metastore-lib for the given dataset.
    '''
    backend = get_metastore_backend()

    return backend.fetch(dataset_name).revision


def get_dataset_version(package_id, revision_ref):
    '''Get the DatasetVersion for a package and revision_ref.
    '''
    version = model.Session.query(DatasetVersion).\
        filter(DatasetVersion.package_id == package_id).\
        filter(DatasetVersion.package_revision_id == revision_ref).\
        one_or_none()

    if not version:
        raise toolkit.ObjectNotFound('Version not found')

    return version.as_dict()
