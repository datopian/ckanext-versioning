from ckan import model
from ckan.lib import helpers as h
from ckan.plugins import toolkit
from flask import Blueprint

versioning = Blueprint('versioning', __name__)

def show(package_id, revision_ref=None):
    context = {
        'model': model, 'session': model.Session,
        'user': toolkit.c.user, 'for_view': True,
        'auth_user_obj': toolkit.c.userobj
    }

    data_dict = {'id':package_id, 'include_tracking': True}
    if revision_ref:
        data_dict['revision_ref'] = revision_ref

    pkg_dict = toolkit.get_action('package_show')(context, data_dict)

    toolkit.c.pkg_dict = pkg_dict

    return toolkit.render('package/read.html')


def changes(id):
    context = {
        'model': model, 'user': toolkit.c.user
    }

    try:
        # We'll need this for the title / breadcrumbs, etc
        current_pkg_dict = toolkit.get_action('package_show')(
            context, {'id': id})
    except toolkit.NotAuthorized:
        toolkit.abort(401, 'Not authorized to read dataset')

    versions = toolkit.get_action('dataset_version_list')(
        context, {'dataset': id})

    version_id_1 = toolkit.request.args.get('version_id_1')
    version_id_2 = toolkit.request.args.get('version_id_2')

    if version_id_1 and version_id_2:
        try:
            diff = toolkit.get_action('dataset_versions_diff')(
                context, {
                    'id': id,
                    'version_id_1': version_id_1,
                    'version_id_2': version_id_2,
                    'diff_type': 'html',
                }
            )
        except (toolkit.ValidationError, toolkit.ObjectNotFound) as e:
            h.flash_error(toolkit._('Errors found: {}').format(e))
            return toolkit.render(
                'package/version_changes.html', {
                    'pkg_dict': current_pkg_dict,
                    'versions': versions
                }
            )
    else:
        diff = None

    return toolkit.render(
        'package/version_changes.html', {
            'diff': diff,
            'pkg_dict': current_pkg_dict,
            'versions': versions,
            'version_id_1': version_id_1,
            'version_id_2': version_id_2,
        }
    )


versioning.add_url_rule('/dataset/<id>/version/changes', view_func=changes)
versioning.add_url_rule('/dataset/<package_id>/show', view_func=show)
versioning.add_url_rule('/dataset/<package_id>/show/<revision_ref>', view_func=show)
