from ckan.tests import helpers

from ckanext.versioning import model
from metastore.backend import create_metastore

mocked_action = 'ckanext.versioning.logic.action._get_github_backend'
mocked_backend = create_metastore('filesystem', dict(uri='mem://'))


class FunctionalTestBase(helpers.FunctionalTestBase):

    _load_plugins = ['versioning']

    def setup(self):
        if not model.tables_exist():
            model.create_tables()
        super(FunctionalTestBase, self).setup()
