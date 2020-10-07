from ckan import model
from ckan.lib import helpers as h
from ckan.plugins import toolkit
from flask import Blueprint

from ckanext.versioning.logic import helpers

versioning = Blueprint('versioning', __name__)


def show(package_id, revision_ref=None):
    pkg_dict = _get_package(package_id, revision_ref)
    toolkit.c.pkg_dict = pkg_dict
    return toolkit.render('package/read.html')


def resource_show(package_id, resource_id, revision_ref=None):
    """Show a resource of a package, optionally in a given revision / release
    """
    pkg_dict = _get_package(package_id, revision_ref)
    resource = helpers.find_resource_in_package(pkg_dict, resource_id)

    if resource is None:
        raise toolkit.ObjectNotFound("Resource not found for dataset revision")

    # This is here to maintain compatibility with PackageController.resource_read()
    # TODO: clean up and possibly backport 2.9 code so this is cleaner

    toolkit.c.package = pkg_dict
    toolkit.c.pkg_dict = pkg_dict
    toolkit.c.resource = resource
    toolkit.c.pkg = None

    resource_views = toolkit.get_action('resource_view_list')(
        _get_context(), {'id': resource_id})
    resource['has_views'] = len(resource_views) > 0

    current_resource_view = None
    view_id = toolkit.request.args.get('view_id')
    if resource['has_views']:
        if view_id:
            current_resource_view = [rv for rv in resource_views
                                     if rv['id'] == view_id]
            if len(current_resource_view) == 1:
                current_resource_view = current_resource_view[0]
            else:
                raise toolkit.ObjectNotFound("Resource view not found")
        else:
            current_resource_view = resource_views[0]

    template_vars = {'resource_views': resource_views,
                     'current_resource_view': current_resource_view,
                     'dataset_type': pkg_dict['type'] or 'dataset'}

    return toolkit.render('package/resource_read.html',
                          extra_vars=template_vars)


def changes(id):
    context = _get_context()

    try:
        # We'll need this for the title / breadcrumbs, etc
        current_pkg_dict = toolkit.get_action('package_show')(
            context, {'id': id})
    except toolkit.NotAuthorized:
        toolkit.abort(401, 'Not authorized to read dataset')

    releases = toolkit.get_action('dataset_release_list')(
        context, {'dataset': id})

    revision_ref_1 = toolkit.request.args.get('revision_ref_1')
    revision_ref_2 = toolkit.request.args.get('revision_ref_2')

    if revision_ref_1 and revision_ref_2:
        try:
            diff = toolkit.get_action('dataset_release_diff')(
                context, {
                    'id': id,
                    'revision_ref_1': revision_ref_1,
                    'revision_ref_2': revision_ref_2,
                    'diff_type': 'html',
                }
            )
        except (toolkit.ValidationError, toolkit.ObjectNotFound) as e:
            h.flash_error(toolkit._('Errors found: {}').format(e))
            return toolkit.render(
                'package/version_changes.html', {
                    'pkg_dict': current_pkg_dict,
                    'releases': releases
                }
            )
    else:
        diff = None

    return toolkit.render(
        'package/version_changes.html', {
            'diff': diff,
            'pkg_dict': current_pkg_dict,
            'releases': releases,
            'revision_ref_1': revision_ref_1,
            'revision_ref_2': revision_ref_2,
        }
    )


versioning.add_url_rule('/dataset/<id>/release/changes', view_func=changes)
versioning.add_url_rule('/dataset/<package_id>/show', view_func=show)
versioning.add_url_rule('/dataset/<package_id>/show/<revision_ref>', view_func=show)
versioning.add_url_rule('/dataset/<package_id>/resource/<resource_id>', view_func=resource_show)
versioning.add_url_rule('/dataset/<package_id>/show/<revision_ref>/<resource_id>', view_func=resource_show)


def _get_package(package_id, revision_ref=None):
    """Get package, optionally in a revision

    This is factored out as it is used by both show and resource_show views
    """
    context = _get_context()
    data_dict = {'id': package_id, 'include_tracking': True}
    if revision_ref:
        data_dict['revision_ref'] = revision_ref

    return toolkit.get_action('package_show')(context, data_dict)


def _get_context():
    """Get context for actions
    """
    return {'model': model,
            'session': model.Session,
            'user': toolkit.c.user,
            'for_view': True,
            'auth_user_obj': toolkit.c.userobj}
