# encoding: utf-8
import difflib
import json
import logging
import re

from ckan import model as core_model
from ckan.logic.action.get import package_show as core_package_show
from ckan.logic.action.get import resource_show as core_resource_show
from ckan.plugins import toolkit
from metastore.backend import exc

from ckanext.versioning.common import create_author_from_context, get_metastore_backend, tag_to_dict
from ckanext.versioning.datapackage import frictionless_to_dataset, update_ckan_dict
from ckanext.versioning.logic import helpers as h

log = logging.getLogger(__name__)


def dataset_tag_update(context, data_dict):
    """Update a version from the current dataset.

    :param dataset: the id or name of the dataset
    :type dataset: string
    :param tag: the id of the version
    :type tag: string
    :param name: A short name for the version
    :type name: string
    :param description: A description for the version
    :type description: string
    :returns: the edited version
    :rtype: dictionary
    """
    import ipdb; ipdb.set_trace()
    tag, name, dataset_name_or_id = toolkit.get_or_bust(
        data_dict, ['tag', 'name', 'dataset']
        )

    toolkit.check_access('dataset_tag_create', context, data_dict)
    assert context.get('auth_user_obj')  # Should be here after `check_access`

    backend = get_metastore_backend()
    author = create_author_from_context(context)
    try:
        tag_info = backend.tag_update(
                _get_dataset_name(dataset_name_or_id),
                tag,
                new_name=name,
                new_description=data_dict.get('description', None),
                author=author
                )
    except exc.NotFound:
        raise toolkit.ObjectNotFound("Dataset version not found.")

    log.info('Version "%s" with id %s edited correctly', name, tag)

    return tag_to_dict(tag_info)


def dataset_tag_create(context, data_dict):
    """Create a new version from the current dataset's revision

    Currently you must have editor level access on the dataset
    to create a version.

    :param dataset: the id or name of the dataset
    :type dataset: string
    :param name: A short name for the version
    :type name: string
    :param description: A description for the version
    :type description: string
    :returns: the newly created version
    :rtype: dictionary
    """
    model = context.get('model', core_model)
    dataset_id_or_name, name = toolkit.get_or_bust(
        data_dict, ['dataset', 'name'])
    dataset = model.Package.get(dataset_id_or_name)
    if not dataset:
        raise toolkit.ObjectNotFound('Dataset not found')

    toolkit.check_access('dataset_tag_create', context, data_dict)
    assert context.get('auth_user_obj')  # Should be here after `check_access`

    # TODO: Names like 'Version 1.2' are not allowed as Github tags
    backend = get_metastore_backend()
    author = create_author_from_context(context)
    current_revision = backend.fetch(dataset.name)
    try:
        tag_info = backend.tag_create(
                dataset.name,
                current_revision.revision,
                name,
                description=data_dict.get('description', None),
                author=author
                )
    except exc.Conflict as e:
        #  Name not unique
        log.debug("Version name already exists: %s", e)
        raise toolkit.ValidationError(
            'Version names must be unique per dataset'
        )

    log.info('Version "%s" created for package %s', name, dataset.id)

    return tag_to_dict(tag_info)


def dataset_tag_promote(context, data_dict):
    """ Promotes a dataset version to the current state of the dataset.

    param version: the version to be promoted
    type version: string
    """
    import ipdb; ipdb.set_trace()
    version = dataset_tag_show(context, data_dict)

    if not version:
        raise toolkit.ObjectNotFound('Version not found')

    data_dict['dataset'] = version['package_id']
    toolkit.check_access('dataset_tag_create', context, data_dict)
    assert context.get('auth_user_obj')  # Should be here after `check_access`

    revision_dict = toolkit.get_action('package_show')(context, {
        'id': version['package_id'],
        'tag': version['name']
    })

    promoted_dataset = toolkit.get_action('package_update')(
        context, revision_dict)

    log.info(
        'Version "%s" promoted as latest for package %s',
        version['name'],
        promoted_dataset['title'])

    return promoted_dataset


@toolkit.side_effect_free
def dataset_tag_list(context, data_dict):
    """List versions of a given dataset

    :param dataset: the id or name of the dataset
    :type dataset: string
    :returns: list of matched versions
    :rtype: list
    """
    model = context.get('model', core_model)
    dataset_id_or_name = toolkit.get_or_bust(data_dict, ['dataset'])
    dataset = model.Package.get(dataset_id_or_name)
    if not dataset:
        raise toolkit.ObjectNotFound('Dataset not found')

    backend = get_metastore_backend()

    tag_list = backend.tag_list(dataset.name)

    return [tag_to_dict(t) for t in tag_list]


@toolkit.side_effect_free
def dataset_tag_show(context, data_dict):
    """Get a specific version by ID

    :param dataset: the name of the dataset
    :type dataset: string
    :param tag: the id of the version
    :type tag: string
    :returns: The matched version
    :rtype: dict
    """
    dataset_name, tag = toolkit.get_or_bust(data_dict, ['dataset', 'tag'])
    backend = get_metastore_backend()
    try:
        tag_info = backend.tag_fetch(dataset_name, tag)
    except exc.NotFound:
        raise toolkit.ObjectNotFound('Dataset version not found.')

    return tag_to_dict(tag_info)


def dataset_tag_delete(context, data_dict):
    """Delete a specific version of a dataset

    :param dataset: name of the dataset
    :type dataset: string
    :param tag: the id of the version
    :type tag: string
    :returns: The matched version
    :rtype: dict
    """
    dataset_name, tag = toolkit.get_or_bust(data_dict, ['dataset', 'tag'])

    backend = get_metastore_backend()
    try:
        backend.tag_delete(dataset_name, tag)
    except Exception:
        raise toolkit.ObjectNotFound('Dataset version not found')

    log.info('Version %s of dataset %s was deleted',
             tag, dataset_name)


@toolkit.side_effect_free
def package_show_revision(context, data_dict):
    """Show a package from a specified revision

    Takes the same arguments as 'package_show' but with an additional
    revision ID parameter

    :param id: the id of the package
    :type id: string
    :param tag: the ID of the revision
    :type tag: string
    :returns: A package dict
    :rtype: dict
    """
    tag = data_dict.get('tag')
    if tag is None:
        result = core_package_show(context, data_dict)
    else:
        result = _get_package_in_revision(context, data_dict, tag)

    return result


@toolkit.side_effect_free
def package_show_tag(context, data_dict):
    """Wrapper for package_show with some additional version related info

    This works just like package_show but also optionally accepts `version_id`
    as a parameter; Providing it means that the returned data will show the
    package metadata from the specified version, and also include the
    version_metadata key with some version metadata.

    If version_id is not provided, package data will include a `versions` key
    with a list of versions for this package.
    """
    tag = data_dict.get('tag', None)
    dataset_name = data_dict.get('dataset', None)
    if tag and dataset_name:
        version_dict = dataset_tag_show(
            context, {'tag': tag, 'dataset': dataset_name}
            )
        package_dict = _get_package_in_revision(
            context, data_dict, version_dict['name'])
        package_dict['version_metadata'] = version_dict
    else:
        package_dict = core_package_show(context, data_dict)
        versions = dataset_tag_list(context, {'dataset': package_dict['id']})
        package_dict['versions'] = versions

    return package_dict


@toolkit.side_effect_free
def resource_show_revision(context, data_dict):
    """Show a resource from a specified revision

    Takes the same arguments as 'resource_show' but with an additional
    revision ID parameter

    Revision ID can also be specified as part of the package ID, as
    <resource_id>@<revision_id>.

    :param id: the id of the resource
    :type id: string
    :param revision_id: the ID of the revision
    :type revision_id: string
    :returns: A resource dict
    :rtype: dict
    """
    dd = data_dict.copy()
    if data_dict.get('revision_id') is None and '@' in data_dict['id']:
        resource_id, revision_id = data_dict['id'].split('@', 1)
        dd.update({'id': resource_id})
        rsc = _get_resource_in_revision(context, dd, revision_id)
    else:
        rsc = core_resource_show(context, data_dict)
        if 'revision_id' in context:
            rsc = _fix_resource_data(rsc, context['revision_id'])

    return rsc


@toolkit.side_effect_free
def resource_show_tag(context, data_dict):
    """Wrapper for resource_show allowing to get a resource from a specific
    dataset version
    """
    version_id = data_dict.get('version_id', None)
    if version_id:
        version_dict = dataset_tag_show(context, {'id': version_id})
        resource_dict = _get_resource_in_revision(
            context, data_dict, version_dict['package_revision_id'])
        resource_dict['version_metadata'] = version_dict
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
        if resource_dict['id'] in url:
            rsc_id = '{}@{}'.format(resource_dict['id'], revision_id)
            url = url.replace(resource_dict['id'], rsc_id)

        if resource_dict['package_id'] in url:
            pkg_id = '{}@{}'.format(resource_dict['package_id'], revision_id)
            url = url.replace(resource_dict['package_id'], pkg_id)

        resource_dict['url'] = url

    return resource_dict


@toolkit.side_effect_free
def dataset_versions_diff(context, data_dict):
    '''Returns a diff between two dataset versions

    :param id: the id of the dataset
    :type id: string
    :param version_id_1: the id of the first version to compare
    :type id: string
    :param version_id_2: the id of the second version to compare
    :type id: string
    :param diff_type: 'unified', 'context', 'html'
    :type diff_type: string

    '''

    dataset_id, tag_1, tag_2 = toolkit.get_or_bust(
        data_dict, ['id', 'tag_1', 'tag_2'])
    diff_type = data_dict.get('diff_type', 'unified')

    toolkit.check_access(
        u'dataset_versions_diff',
        context,
        {'name_or_id': dataset_id}
    )

    dataset_version_1 = _get_dataset_version_dict(
        context, dataset_id, tag_1)
    dataset_version_2 = _get_dataset_version_dict(
        context, dataset_id, tag_2)

    diff = _generate_diff(dataset_version_1, dataset_version_2, diff_type)

    return {
        'diff': diff,
        'dataset_dict_1': dataset_version_1,
        'dataset_dict_2': dataset_version_2,
    }


def _get_dataset_version_dict(context, dataset_id, tag):

    dataset_dict = toolkit.get_action('package_show')(
        context, {'id': dataset_id})

    if tag != 'current':
        version_dict = toolkit.get_action('dataset_tag_show')(
            context, {'tag': tag, 'dataset': dataset_dict['name']})

        if not version_dict['package_id'] == dataset_dict['name']:
            raise toolkit.ValidationError(
                'You can only compare versions of the same dataset')

        dataset_dict = toolkit.get_action('package_show_tag')(
            context, {
                'tag': version_dict['name'],
                'dataset': version_dict['package_id'],
                'id': dataset_dict['id']
            }
        )
        # Fetching the license_url from the license registry
        if dataset_dict['license_id']:
            _license = h.get_license(
                dataset_dict['license_id'])
            dataset_dict['license_url'] = _license.url
            dataset_dict['license_title'] = _license.title
        dataset_dict.pop('version_metadata', None)

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
