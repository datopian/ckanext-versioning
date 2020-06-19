from ckan.tests import factories
from ckan.tests import helpers as test_helpers
from nose.tools import assert_equals

from ckanext.versioning.logic import helpers
from ckanext.versioning.tests import MetastoreBackendTestBase


class TestHelpers(MetastoreBackendTestBase):

    def setup(self):
        super(TestHelpers, self).setup()

        self.admin_user = factories.Sysadmin()

        self.org = factories.Organization(
            users=[
                {'name': self.admin_user['name'], 'capacity': 'admin'},
            ]
        )
        self.dataset = factories.Dataset(owner_org=self.org['id'],
                                         private=False)

    def test_dataset_has_link_resources(self):
        upload_resource = factories.Resource(
            package_id=self.dataset['id'],
            url_type='upload'
        )
        link_resource = factories.Resource(
            package_id=self.dataset['id'],
            url_type=''
        )

        self.dataset['resources'].extend([upload_resource, link_resource])

        assert_equals(
            helpers.has_link_resources(self.dataset),
            True)

    def test_dataset_does_not_has_link_resources(self):
        upload_resource = factories.Resource(
            package_id=self.dataset['id'],
            url_type='upload'
        )

        self.dataset['resources'].append(upload_resource)

        assert_equals(
            helpers.has_link_resources(self.dataset),
            False)

    def test_get_dataset_revision_list(self):
        context = self._get_context(self.admin_user)
        revision_list = helpers.get_dataset_revision_list(self.dataset['name'])
        assert_equals(len(revision_list), 1)

        test_helpers.call_action(
            'package_update',
            context,
            name=self.dataset['name'],
            title='New Title',
            notes='New Notes'
        )

        revision_list = helpers.get_dataset_revision_list(self.dataset['name'])
        assert_equals(len(revision_list), 2)
