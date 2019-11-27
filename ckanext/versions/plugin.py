# encoding: utf-8

import logging

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit

from ckanext.versions.logic import action, auth, helpers, uploader
from ckanext.versions.model import tables_exist

log = logging.getLogger(__name__)


class VersionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.IUploader, inherit=True)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        if not tables_exist():
            log.critical(
                "The versions extension requires a database setup. Please run "
                "the following to create the database tables: \n"
                "paster --plugin=ckanext-versions versions init-db"
            )
        else:
            log.debug("Dataset versions tables verified to exist")

        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'versions')

    # IActions

    def get_actions(self):
        return {
            'dataset_version_create': action.dataset_version_create,
            'dataset_version_delete': action.dataset_version_delete,
            'dataset_version_list': action.dataset_version_list,
            'dataset_version_update': action.dataset_version_update,
            'dataset_version_show': action.dataset_version_show,
            'package_show_version': action.package_show_version,
            'resource_show_version': action.resource_show_version,

            # Overridden
            'package_show': action.package_show_revision,
            'resource_show': action.resource_show_revision
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'dataset_version_create': auth.dataset_version_create,
            'dataset_version_delete': auth.dataset_version_delete,
            'dataset_version_list': auth.dataset_version_list,
            'dataset_version_show': auth.dataset_version_show,
        }

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'url_for_version': helpers.url_for_version,
            'url_for_resource_version': helpers.url_for_resource_version,
            'dataset_version_has_link_resources': helpers.has_link_resources,
        }

    # IPackageController

    def before_view(self, pkg_dict):
        try:
            versions = action.dataset_version_list({"ignore_auth": True},
                                                   {"dataset": pkg_dict['id']})
        except toolkit.ObjectNotFound:
            # Do not blow up if package is gone
            return pkg_dict

        pkg_dict.update({'versions': versions})

        version_id = toolkit.request.params.get('version', None)
        if version_id:
            version = action.dataset_version_show({"ignore_auth": True},
                                                  {"id": version_id})
            toolkit.c.current_version = version

            # Hide package creation / update date if viewing a specific version
            pkg_dict['metadata_created'] = None
            pkg_dict['metadata_updated'] = None

        return pkg_dict

    # IResourceController

    def before_delete(self, context, resource, resources):
        pass

    # IUploader

    def get_resource_uploader(self, data_dict):
        return uploader.get_uploader(self, data_dict)
