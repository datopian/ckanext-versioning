# encoding: utf-8
import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.versioning import blueprints
from ckanext.versioning.common import create_author_from_context, get_metastore_backend
from ckanext.versioning.datapackage import dataset_to_frictionless
from ckanext.versioning.logic import action, auth, helpers

log = logging.getLogger(__name__)


class PackageVersioningPlugin(plugins.SingletonPlugin,
                              toolkit.DefaultDatasetForm):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IDatasetForm, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'versioning')

    # IActions

    def get_actions(self):
        return {
            'dataset_release_create': action.dataset_release_create,
            'dataset_release_delete': action.dataset_release_delete,
            'dataset_release_list': action.dataset_release_list,
            'dataset_release_update': action.dataset_release_update,
            'dataset_release_show': action.dataset_release_show,
            'dataset_revert': action.dataset_revert,
            'package_show_release': action.package_show_release,
            'resource_show_release': action.resource_show_release,
            'dataset_release_diff': action.dataset_release_diff,

            # Chained to core actions
            'dataset_purge': action.dataset_purge,

            # Overridden core actions
            'package_show': action.package_show_revision,
            'resource_show': action.resource_show_revision,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'dataset_release_create': auth.dataset_release_create,
            'dataset_release_delete': auth.dataset_release_delete,
            'dataset_release_list': auth.dataset_release_list,
            'dataset_release_show': auth.dataset_release_show,
            'dataset_revert': auth.dataset_revert,
            'dataset_release_diff': auth.dataset_release_diff,
        }

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'url_for_revision': helpers.url_for_revision,
            'dataset_has_link_resources': helpers.has_link_resources,
            'dataset_release_compare_pkg_dicts': helpers.compare_pkg_dicts,
            'tojson': helpers.tojson,
            'versioning_get_query_param': helpers.get_query_param,
        }

    # IPackageController

    def before_view(self, pkg_dict):

        try:
            revision_ref = toolkit.request.view_args['revision_ref']
        except (AttributeError, KeyError):
            # TODO: How to correctly access to a request arg in CKAN?
            return pkg_dict

        if get_metastore_backend().is_valid_revision_id(revision_ref):
            releases = action.dataset_release_list({"ignore_auth": True},
                                                   {'dataset': pkg_dict['name']})
            revision = filter(lambda d: d['revision_ref'] == revision_ref,
                              releases)[0]
        else:
            revision = action.dataset_release_show({"ignore_auth": True},
                                                   {'dataset': pkg_dict['name'],
                                                    'release': revision_ref})

        # current_release needs to be a release (eg, name and description).
        # This assumes that there is a release for the given revision
        toolkit.c.current_release = revision

        # Hide package creation / update date if viewing a specific release
        pkg_dict['metadata_created'] = None
        pkg_dict['metadata_updated'] = None
        return pkg_dict

    def after_create(self, context, pkg_dict):
        """Creates a datapackage.json using metastore-lib backend.

        After creating the package, it calls metastore-lib to create a new
        GitHub repository a store the package dict in a datapackage.json file.
        """

        if pkg_dict['type'] == 'dataset':
            datapackage = dataset_to_frictionless(pkg_dict)
            backend = get_metastore_backend()
            author = create_author_from_context(context)
            pkg_info = backend.create(
                pkg_dict['name'],
                datapackage,
                author=author
                )

            log.info(
                'Package {} created correctly. Revision {} created.'.format(
                 pkg_info.package_id, pkg_info.revision
                ))

        return pkg_dict

    def after_update(self, context, pkg_dict):
        """Updates the datapackage.json using metastore-lib backend.

        After updating the package it calls metastore-lib to update the
        datapackage.json file in the GitHub repository.
        """
        if pkg_dict['type'] == 'dataset':
            # We need to get a complete dict to also update resources data.
            # We need to save tracking_summary, required for templates.
            pkg_dict = toolkit.get_action('package_show')({}, {
                'id': pkg_dict['id'],
                'include_tracking': True
                })

            datapackage = dataset_to_frictionless(pkg_dict)
            backend = get_metastore_backend()
            author = create_author_from_context(context)
            pkg_info = backend.update(
                pkg_dict['name'], datapackage, author=author)

            log.info(
                'Package {} updated correctly. Revision {} created.'.format(
                 pkg_info.package_id, pkg_info.revision
                ))

        return pkg_dict

    # IBlueprint

    def get_blueprint(self):
        return [blueprints.versioning]

    # IDatasetForm

    def is_fallback(self):
        return False

    def package_types(self):
        return []
