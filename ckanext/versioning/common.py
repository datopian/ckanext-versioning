import contextlib
from ast import literal_eval

from ckan.plugins import toolkit
from metastore.backend import StorageBackend, create_metastore
from metastore.types import Author


def get_metastore_backend():
    # type: () -> StorageBackend
    '''Returns a metastore object.

    The type and the configuration of the metastore object is defined in the
    configuration file of CKAN.
    '''
    backend_type = toolkit.config.get('ckanext.versioning.backend_type')
    try:
        config = literal_eval(
            toolkit.config.get('ckanext.versioning.backend_config')
        )
    except ValueError:
        config = {}

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


def tag_to_dict(tag):
    ''' Returns a dict version of a TagInfo object

    # TODO: Refactor or move it to metastore-lib
    '''
    return {
        'package_id': tag.package_id,
        'name': tag.name,
        'created': tag.created.isoformat(),
        'revision_ref': tag.revision_ref,
        'author': tag.author.name,
        'author_email': tag.author.email,
        'description': tag.description
    }


@contextlib.contextmanager
def exception_mapper(from_exc, to_exc):
    """A context manager that maps ``from_exc`` exceptions to ``to_exc``.

    This is highly useful if all you want is to catch exceptions thrown by an
    lower-level library and map them into higher level exceptions with specific
    semantics.
    """
    try:
        yield
    except from_exc as e:
        raise to_exc(e)
