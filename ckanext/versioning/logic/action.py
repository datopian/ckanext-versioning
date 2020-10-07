# encoding: utf-8
import difflib
import json
import logging
import re

from ckan import model as core_model
from ckan.common import request
from ckan.logic.action.get import package_show as core_package_show
from ckan.logic.action.get import resource_show as core_resource_show
from ckan.plugins import toolkit
from metastore.backend import exc
from six.moves.urllib import parse

from ckanext.versioning.common import create_author_from_context, exception_mapper, get_metastore_backend, tag_to_dict
from ckanext.versioning.datapackage import frictionless_to_dataset, update_ckan_dict
from ckanext.versioning.logic import helpers as h

log = logging.getLogger(__name__)


def dataset_release_update(context, data_dict):
    """Update a release of the current dataset.

    :param dataset: the id or name of the dataset
    :type dataset: string
    :param release: the id of the release
    :type release: string
    :param name: A short name for the release
    :type name: string
    :param description: A description for the release
    :type description: string
    :returns: the edited release
    :rtype: dictionary
    """
    release, name, dataset_name_or_id = toolkit.get_or_bust(
        data_dict, ['release', 'name', 'dataset']
        )

    toolkit.check_access('dataset_release_create', context, data_dict)
    assert context.get('auth_user_obj')  # Should be here after `check_access`

    backend = get_metastore_backend()
    author = create_author_from_context(context)
    try:
        release_info = backend.tag_update(
                _get_dataset_name(dataset_name_or_id),
                release,
                new_name=name,
                new_description=data_dict.get('description', None),
                author=author
                )
    except exc.NotFound:
        raise toolkit.ObjectNotFound("Dataset release not found.")

    log.info('Release "%s" with id %s modified successfully', name, release)

    return tag_to_dict(release_info)


def dataset_release_create(context, data_dict):
    """Create a new release from the current dataset's revision

    Currently you must have editor level access on the dataset
    to create a release.

    :param dataset: the id or name of the dataset
    :type dataset: string
    :param name: A short name for the release
    :type name: string
    :param description: A description for the release
    :type description: string
    :returns: the newly created release
    :rtype: dictionary
    """
    model = context.get('model', core_model)
    dataset_id_or_name, name = toolkit.get_or_bust(
        data_dict, ['dataset', 'name'])
    dataset = model.Package.get(dataset_id_or_name)
    if not dataset:
        raise toolkit.ObjectNotFound('Dataset not found')

    toolkit.check_access('dataset_release_create', context, data_dict)
    assert context.get('auth_user_obj')  # Should be here after `check_access`

    # TODO: Names like 'Version 1.2' are not allowed as Github tags
    backend = get_metastore_backend()
    author = create_author_from_context(context)
    current_revision = backend.fetch(dataset.name)
    try:
        release_info = backend.tag_create(
                dataset.name,
                current_revision.revision,
                name,
                description=data_dict.get('description', None),
                author=author
                )
    except exc.Conflict as e:
        #  Name not unique
        log.debug("Release already exists: %s", e)
        raise toolkit.ValidationError('Release names must be unique per dataset')

    log.info('Release "%s" created for package %s', name, dataset.id)

    return tag_to_dict(release_info)


def dataset_revert(context, data_dict):
    """Reverts a dataset to a specified revision or release

    param dataset: the dataset name or ID to be reverted
    type dataset: string
    param revision_ref: the release or revision to revert to
    type revision_ref: string
    """
    dataset_id, revision_ref = toolkit.get_or_bust(
        data_dict, ['dataset', 'revision_ref'])

    toolkit.check_access('dataset_revert', context, data_dict)
    assert context.get('auth_user_obj')  # Should be here after `check_access`

    revision_dict = toolkit.get_action('package_show')(context, {
        'id': dataset_id,
        'revision_ref': revision_ref
    })

    reverted_dataset = toolkit.get_action('package_update')(
        context, revision_dict)

    log.info('Package %s reverted to revision %s', dataset_id, revision_ref)

    return reverted_dataset


@toolkit.side_effect_free
def dataset_release_list(context, data_dict):
    """List releases of a given dataset

    :param dataset: the id or name of the dataset
    :type dataset: string
    :returns: list of matched releases
    :rtype: list
    """
    model = context.get('model', core_model)
    dataset_id_or_name = toolkit.get_or_bust(data_dict, ['dataset'])
    dataset = model.Package.get(dataset_id_or_name)
    if not dataset:
        raise toolkit.ObjectNotFound('Dataset not found')

    backend = get_metastore_backend()

    with exception_mapper(exc.NotFound, toolkit.ObjectNotFound):
        release_list = backend.tag_list(dataset.name)

    return [tag_to_dict(t) for t in release_list]


@toolkit.side_effect_free
def dataset_release_show(context, data_dict):
    """Get a specific release by ID

    :param dataset: the name of the dataset
    :type dataset: string
    :param release: the id of the release
    :type release: string
    :returns: The matched release
    :rtype: dict
    """
    dataset_name, release = toolkit.get_or_bust(data_dict, ['dataset', 'release'])
    backend = get_metastore_backend()
    with exception_mapper(exc.NotFound, toolkit.ObjectNotFound):
        release_info = backend.tag_fetch(dataset_name, release)

    return tag_to_dict(release_info)


def dataset_release_delete(context, data_dict):
    """Delete a specific release of a dataset

    :param dataset: name of the dataset
    :type dataset: string
    :param release: the id of the release
    :type release: string
    :returns: The matched release
    :rtype: dict
    """
    dataset_name, release = toolkit.get_or_bust(data_dict, ['dataset', 'release'])

    backend = get_metastore_backend()
    try:
        backend.tag_delete(dataset_name, release)
    except Exception:
        raise toolkit.ObjectNotFound('Dataset release not found')

    log.info('Release %s of dataset %s was deleted', release, dataset_name)


@toolkit.side_effect_free
def package_show_revision(context, data_dict):
    """Show a package from a specified revision

    Takes the same arguments as 'package_show' but with an additional
    revision ID parameter

    :param id: the id of the package
    :type id: string
    :param revision_ref: the ID of the revision
    :type revision_ref: string
    :returns: A package dict
    :rtype: dict
    """
    revision_ref = _get_revision_ref(data_dict)
    if revision_ref is None:
        result = core_package_show(context, data_dict)
    else:
        result = _get_package_in_revision(context, data_dict, revision_ref)

    return result


@toolkit.side_effect_free
def package_show_release(context, data_dict):
    """Wrapper for package_show with some additional release related info

    This works just like package_show but also optionally accepts `release_id`
    as a parameter; Providing it means that the returned data will show the
    package metadata from the specified release, and also include the
    release_metadata key with some release metadata.

    If release_id is not provided, package data will include a `releases` key
    with a list of releases for this package.
    """
    release = data_dict.get('release', None)
    dataset_name = data_dict.get('dataset', None)
    if release and dataset_name:
        release_dict = dataset_release_show(
            context, {'release': release, 'dataset': dataset_name}
            )
        package_dict = _get_package_in_revision(
            context, data_dict, release_dict['name'])
        package_dict['release_metadata'] = release_dict
    else:
        package_dict = core_package_show(context, data_dict)
        releases = dataset_release_list(context, {'dataset': package_dict['id']})
        package_dict['releases'] = releases

    return package_dict


@toolkit.side_effect_free
def resource_show_revision(context, data_dict):
    """Show a resource from a specified revision

    Takes the same arguments as 'resource_show' but with an additional
    revision_ref parameter

    :param id: the id of the resource
    :type id: string
    :param revision_ref: the ID of the revision or release name
    :type revision_ref: string
    :returns: A resource dict
    :rtype: dict
    """
    revision_ref = _get_revision_ref(data_dict)
    if revision_ref is None:
        return core_resource_show(context, data_dict)

    model = context['model']
    id = toolkit.get_or_bust(data_dict, 'id')
    resource = model.Resource.get(id)

    package = _get_package_in_revision(context, {'id': resource.package_id}, revision_ref)
    resource_dict = h.find_resource_in_package(package, id)
    if resource_dict is None:
        raise toolkit.ObjectNotFound("Resource not found for dataset revision")

    return resource_dict


@toolkit.side_effect_free
def resource_show_release(context, data_dict):
    """Wrapper for resource_show allowing to get a resource from a specific
    dataset release
    """
    release_id = data_dict.get('release_id', None)
    if release_id:
        release_dict = dataset_release_show(context, {'id': release_id})
        resource_dict = _get_resource_in_revision(
            context, data_dict, release_dict['package_revision_id'])
        resource_dict['release_metadata'] = release_dict
        return resource_dict

    else:
        return toolkit.get_action('resource_show')(context, data_dict)


def _get_package_in_revision(context, data_dict, revision_id):
    """Internal implementation of package_show_revision
    """
    result = core_package_show(context, data_dict)
    if revision_id:
        backend = get_metastore_backend()
        dataset_name = _get_dataset_name(data_dict.get('id'))
        pkg_info = backend.fetch(dataset_name, revision_id)
        dataset = frictionless_to_dataset(pkg_info.package)
        result = update_ckan_dict(result, dataset)
        for resource in result.get('resources', []):
            resource['datastore_active'] = False
            _fix_resource_data(resource, revision_id)

    # Fetching the license_url, title from the license registry and validate
    if 'license_id' in result and result['license_id']:
        license_data = h.get_license(result['license_id'])
        # Validate license has url and title both
        result['license_url'] = license_data.url if license_data.url else ''
        result['license_title'] = license_data.title if license_data.title \
            else ''
    return result


def _get_resource_in_revision(context, data_dict, revision_id):
    """Get resource from a given revision
    """
    current_revision_id = context.get('revision_id', None)
    context['revision_id'] = revision_id
    result = core_resource_show(context, data_dict)
    result['datastore_active'] = False
    _fix_resource_data(result, revision_id)

    if current_revision_id:
        context['revision_id'] = current_revision_id
    else:
        del context['revision_id']

    return result


def _fix_resource_data(resource_dict, revision_id):
    """Make some adjustments to the resource dict if we are showing a revision
    of a package
    """
    url = resource_dict.get('url')
    if url and resource_dict.get('url_type') == 'upload' and '://' in url:
        # Resource is pointing at a local uploaded file, which has already been
        # converted to an absolute URL by `model_dictize.resource_dictized`
        parts = list(parse.urlsplit(url))
        parts[3] = '{}{}revision_ref={}'.format(parts[3],
                                                '&' if parts[3] else '',
                                                revision_id)
        resource_dict['url'] = parse.urlunsplit(parts)

    return resource_dict


@toolkit.side_effect_free
def dataset_release_diff(context, data_dict):
    '''Returns a diff between two dataset releases

    :param id: the id of the dataset
    :type id: string
    :param revision_ref_1: the id of the first release to compare
    :type id: string
    :param revision_ref_2: the id of the second release to compare
    :type id: string
    :param diff_type: 'unified', 'context', 'html'
    :type diff_type: string

    '''

    dataset_id, revision_ref_1, revision_ref_2 = toolkit.get_or_bust(
        data_dict, ['id', 'revision_ref_1', 'revision_ref_2'])
    diff_type = data_dict.get('diff_type', 'unified')

    toolkit.check_access(u'dataset_release_diff', context,
                         {'name_or_id': dataset_id})

    revision_1 = _get_dataset_revision_dict(context, dataset_id, revision_ref_1)
    revision_2 = _get_dataset_revision_dict(context, dataset_id, revision_ref_2)
    diff = _generate_diff(revision_1, revision_2, diff_type)

    return {
        'diff': diff,
        'dataset_dict_1': revision_1,
        'dataset_dict_2': revision_2,
    }


def _get_dataset_revision_dict(context, dataset_id, revision_ref):

    dataset_dict = toolkit.get_action('package_show')(
        context, {'id': dataset_id})

    if revision_ref != 'current':
        release_dict = toolkit.get_action('dataset_release_show')(
            context, {'release': revision_ref, 'dataset': dataset_dict['name']})

        if not release_dict['package_id'] == dataset_dict['name']:
            raise toolkit.ValidationError(
                'You can only compare revisions of the same dataset')

        dataset_dict = toolkit.get_action('package_show_release')(
            context, {
                'release': release_dict['name'],
                'dataset': release_dict['package_id'],
                'id': dataset_dict['id']
            }
        )
        # Fetching the license_url from the license registry
        if dataset_dict['license_id']:
            _license = h.get_license(
                dataset_dict['license_id'])
            dataset_dict['license_url'] = _license.url
            dataset_dict['license_title'] = _license.title
        dataset_dict.pop('release_metadata', None)

    return dataset_dict


def _generate_diff(obj1, obj2, diff_type):

    def _dump_obj(obj):
        return json.dumps(obj, indent=2, sort_keys=True).split('\n')

    obj_lines = [_dump_obj(obj) for obj in [obj1, obj2]]

    if diff_type == 'unified':
        diff_generator = difflib.unified_diff(*obj_lines)
        diff = '\n'.join(line for line in diff_generator)
    elif diff_type == 'context':
        diff_generator = difflib.context_diff(*obj_lines)
        diff = '\n'.join(line for line in diff_generator)
    elif diff_type == 'html':
        # word-wrap lines. Otherwise you get scroll bars for most datasets.
        for obj_index in (0, 1):
            wrapped_obj_lines = []
            for line in obj_lines[obj_index]:
                wrapped_obj_lines.extend(re.findall(r'.{1,70}(?:\s+|$)', line))
            obj_lines[obj_index] = wrapped_obj_lines
        diff = difflib.HtmlDiff().make_table(*obj_lines)
    else:
        raise toolkit.ValidationError('diff_type not recognized')

    return diff


def _get_dataset_name(id_or_name):
    ''' Returns the dataset name given the id or name '''
    if not core_model.is_id(id_or_name):
        return id_or_name

    dataset = core_model.Package.get(id_or_name)
    if not dataset:
        raise toolkit.ObjectNotFound('Package {} not found'.format(id_or_name))

    return dataset.name


def _get_revision_ref(data_dict):
    """Get the revision_ref parameter from data_dict or query string
    """
    revision_ref = data_dict.get('revision_ref')
    if revision_ref is None:
        try:
            revision_ref = request.params.get('revision_ref')
        except TypeError:
            pass

    return revision_ref


@toolkit.chained_action
def dataset_purge(next_action, context, data_dict):
    """Purge a dataset.

    .. warning:: Purging a dataset cannot be undone!

    This wraps the core ``dataset_purge`` action with code that also removes
    the datapackage from metastore.

    :param id: the name or id of the dataset to be purged
    :type id: string
    """

    # We do not check permissions as we rely on core action to check them
    next_action(context, data_dict)
    assert 'package' in context

    backend = get_metastore_backend()
    try:
        backend.delete(context['package'].name)
    except exc.NotFound as e:
        log.warning("Dataset deleted from DB but not found in metastore: %s; "
                    "Error: %s", context['package'].id, e)
