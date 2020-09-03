from ckan.plugins import toolkit
from ckan.tests import factories
from ckan.tests import helpers as test_helpers
from nose.tools import assert_in

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
        app.get(url, extra_environ=environ, status=200)

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

        release = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

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
            revision_ref=release['revision_ref'])

        environ = {'REMOTE_USER': self.user_name}
        res = app.get(url, extra_environ=environ)

        assert_in(original_notes, res.ubody)

    def test_package_show_renders_release_by_name(self):
        app = self._get_test_app()
        context = self._get_context(self.user)

        release = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

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
            revision_ref=release['name'])

        environ = {'REMOTE_USER': self.user_name}
        res = app.get(url, extra_environ=environ)

        assert_in(original_notes, res.ubody)

    def test_package_show_renders_alert_info(self):
        app = self._get_test_app()
        context = self._get_context(self.user)

        release = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        test_helpers.call_action(
            'package_patch',
            context,
            id=self.dataset['id'],
            notes='Some changed notes',
        )

        url = toolkit.url_for(
            'versioning.show',
            package_id=self.dataset['id'],
            revision_ref=release['revision_ref'])

        environ = {'REMOTE_USER': self.user_name}
        res = app.get(url, extra_environ=environ)

        assert_in('This is an old revision of this dataset', res.ubody)
        assert_in('module info alert alert-info', res.ubody)
