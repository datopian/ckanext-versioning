from ckan.tests import helpers

from ckanext.versioning import model
from metastore.backend.filesystem import FilesystemStorage

mocked_import = 'ckanext.versioning.logic.action.get_metastore_backend'
mocked_backend = FilesystemStorage('mem://')


class FunctionalTestBase(helpers.FunctionalTestBase):

    _load_plugins = ['versioning']

    def setup(self):
        if not model.tables_exist():
            model.create_tables()
        super(FunctionalTestBase, self).setup()
