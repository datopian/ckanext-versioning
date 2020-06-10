from ckan.plugins import toolkit

from metastore.backend.filesystem import FilesystemStorage
from metastore.backend.gh import GitHubStorage


def get_metastore_backend():
    metastore_backend = toolkit.config.get('ckanext.versioning.backend')

    if metastore_backend == 'github':
        token = toolkit.config.get('ckanext.versioning.github_token')
        default_owner = toolkit.config.get('ckanext.versioning.default_owner')
        lfs_server = toolkit.config.get('ckanext.versioning.lfs_server')
        backend = GitHubStorage(
                github_options={"login_or_token": token},
                lfs_server_url=lfs_server,
                default_owner=default_owner
                )
        return backend

    # If not metastore config option use a in-memory one.
    return FilesystemStorage('mem://')
