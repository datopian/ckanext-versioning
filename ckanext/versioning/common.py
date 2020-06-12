from ast import literal_eval

from ckan.plugins import toolkit

from metastore.backend import create_metastore
from metastore.types import Author


def get_metastore_backend():
    '''Returns a metastore object.

    The type and the configuration of the metastore object is defined in the
    configuration file of CKAN.
    '''
    backend_type = toolkit.config.get('ckanext.versioning.backend_type')
    config = literal_eval(
        toolkit.config.get('ckanext.versioning.backend_config')
        )
    return create_metastore(backend_type, config)


def create_author_from_context(context):
    '''Creates an Author object for the current user in the system.
    '''
    user_obj = context['auth_user_obj']
    if user_obj:
        author = Author(user_obj.name, user_obj.email)
    else:
        author = Author(name=context['user'])

    return author
