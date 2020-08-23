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
        toolkit.add_resource('fanstatic', 'versions')

    # IActions

    def get_actions(self):
        return {
            'dataset_tag_create': action.dataset_tag_create,
            'dataset_tag_delete': action.dataset_tag_delete,
            'dataset_tag_list': action.dataset_tag_list,
            'dataset_tag_update': action.dataset_tag_update,
            'dataset_tag_show': action.dataset_tag_show,
            'dataset_revert': action.dataset_revert,
            'package_show_tag': action.package_show_tag,
            'resource_show_tag': action.resource_show_tag,
            'dataset_versions_diff': action.dataset_versions_diff,

            # Overridden
            'package_show': action.package_show_revision,
            'resource_show': action.resource_show_revision,
            'dataset_purge': action.dataset_purge,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'dataset_tag_create': auth.dataset_tag_create,
            'dataset_tag_delete': auth.dataset_tag_delete,
            'dataset_tag_list': auth.dataset_tag_list,
            'dataset_tag_show': auth.dataset_tag_show,
            'dataset_revert': auth.dataset_revert,
            'dataset_versions_diff': auth.dataset_versions_diff,
        }

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'url_for_revision': helpers.url_for_revision,
            'dataset_version_has_link_resources': helpers.has_link_resources,
            'dataset_version_compare_pkg_dicts': helpers.compare_pkg_dicts,
            'tojson': helpers.tojson,
        }

    # IPackageController

    def before_view(self, pkg_dict):
        try:
            versions = action.dataset_tag_list(
                {"ignore_auth": True},
                {"dataset": pkg_dict['id']}
                )
        except toolkit.ObjectNotFound:
            # Do not blow up if package is gone
            return pkg_dict

        toolkit.c.versions = versions

        revision_ref = None
        try:
            revision_ref = toolkit.request.view_args['revision_ref']
        except (AttributeError, KeyError):
            # TODO: How to correctly access to a request arg in CKAN?
            pass

        if revision_ref:
            tag_list = action.dataset_tag_list({}, {
                'dataset': pkg_dict['name']
            })
            if get_metastore_backend().is_valid_revision_id(revision_ref):
                revision = filter(lambda d: d['revision_ref'] == revision_ref, tag_list)[0]
            else:
                revision = filter(lambda d: d['name'] == revision_ref, tag_list)[0]
            # current_version needs to be a Tag (eg, name and description).
            # This assumes that there is a tag for the given revision
            toolkit.c.current_version = revision

            # Hide package creation / update date if viewing a specific version
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
