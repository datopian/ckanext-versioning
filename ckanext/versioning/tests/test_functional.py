from ckan.plugins import toolkit
from ckan.tests import factories
from ckan.tests import helpers as test_helpers
from nose.tools import assert_equals, assert_in, assert_raises

from ckanext.versioning.logic import helpers
from ckanext.versioning.tests import MetastoreBackendTestBase


class TestPackageShow(MetastoreBackendTestBase):

    def setup(self):
        super(TestPackageShow, self).setup()

        self.user = factories.User()
        self.user_name = self.user['name'].encode('utf8')

        self.dataset = factories.Dataset()

    def test_package_read_is_rendered(self):
        app = self._get_test_app()

        url = toolkit.url_for(
            'versioning.show',
            package_id=self.dataset['id'])
        environ = {'REMOTE_USER': self.user_name}
        res = app.get(url, extra_environ=environ)


    def test_package_show_renders_master_if_not_revision(self):
        app = self._get_test_app()

        url = toolkit.url_for(
            'versioning.show',
            package_id=self.dataset['id'])
        environ = {'REMOTE_USER': self.user_name}
        res = app.get(url, extra_environ=environ)
        assert_in(self.dataset['name'], res.ubody)


    def test_package_show_renders_revision(self):
        app = self._get_test_app()
        context = self._get_context(self.user)

        rev_id = helpers.get_dataset_current_revision(self.dataset['name'])
        original_notes = self.dataset['notes']

        test_helpers.call_action(
            'package_patch',
            context,
            id=self.dataset['id'],
            notes='Some changed notes',
        )

        url = toolkit.url_for(
            'versioning.show',
            package_id=self.dataset['id'],
            revision_id=rev_id)

        environ = {'REMOTE_USER': self.user_name}
        res = app.get(url, extra_environ=environ)

        assert_in(original_notes, res.ubody)
