# encoding: utf-8
import logging
from datetime import datetime

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.lib.uploader import ALLOWED_UPLOAD_TYPES

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
            'dataset_tag_promote': action.dataset_tag_promote,
            'package_show_tag': action.package_show_tag,
            'resource_show_tag': action.resource_show_tag,
            'dataset_versions_diff': action.dataset_versions_diff,

            # Overridden
            'package_show': action.package_show_revision,
            'resource_show': action.resource_show_revision,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'dataset_tag_create': auth.dataset_tag_create,
            'dataset_tag_delete': auth.dataset_tag_delete,
            'dataset_tag_list': auth.dataset_tag_list,
            'dataset_tag_show': auth.dataset_tag_show,
            'dataset_versions_diff': auth.dataset_versions_diff,
        }

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'url_for_tag': helpers.url_for_tag,
            'url_for_resource_version': helpers.url_for_resource_version,
            'dataset_version_has_link_resources': helpers.has_link_resources,
            'dataset_version_compare_pkg_dicts': helpers.compare_pkg_dicts,
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

        tag = None
        try:
            tag = toolkit.request.view_args['tag']
        except (AttributeError, KeyError):
            # TODO: How to correctly access to a request arg in CKAN?
            pass

        if tag:
            version = action.dataset_tag_show({}, {
                'dataset': pkg_dict['name'],
                'tag': tag
            })
            toolkit.c.current_version = version

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
