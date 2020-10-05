from ckan.plugins import toolkit
from ckan.tests import factories
from ckan.tests import helpers as test_helpers
from metastore.backend.exc import NotFound
from nose.tools import assert_equals, assert_in, assert_raises, raises

from ckanext.versioning.logic import helpers
from ckanext.versioning.tests import MetastoreBackendTestBase


class TestVersioningActions(MetastoreBackendTestBase):
    """Test cases for logic actions
    """

    def setup(self):
        super(TestVersioningActions, self).setup()

        self.org_admin = factories.User()
        self.org_admin_name = self.org_admin['name'].encode('ascii')

        self.org_member = factories.User()
        self.org_member_name = self.org_member['name'].encode('ascii')

        self.org = factories.Organization(
            users=[
                {'name': self.org_member['name'], 'capacity': 'member'},
                {'name': self.org_admin['name'], 'capacity': 'admin'},
            ]
        )

        self.dataset = factories.Dataset()

    def test_create_release(self):
        """Test basic dataset release creation
        """
        context = self._get_context(self.org_admin)
        release = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        revision = helpers.get_dataset_current_revision(self.dataset['name'])

        assert_equals(release['package_id'], self.dataset['name'])
        assert_equals(release['revision_ref'],
                      revision)
        assert_equals(release['description'],
                      "The best dataset ever, it **rules!**")
        assert_equals(release['author'], self.org_admin['name'])
        assert_equals(release['author_email'], self.org_admin['email'])

    def test_create_release_name_already_exists(self):
        """Test that creating a release with an existing name for the same
        dataset raises an error
        """
        context = self._get_context(self.org_admin)
        test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="HEAD",
            description="The best dataset ever, it **rules!**")

        assert_raises(toolkit.ValidationError, test_helpers.call_action,
                      'dataset_release_create', context,
                      dataset=self.dataset['id'],
                      name="HEAD",
                      description="This is also a good release")

    def test_create_dataset_not_found(self):
        payload = {'dataset': 'abc123',
                   'name': "Release 0.1.2"}

        assert_raises(toolkit.ObjectNotFound, test_helpers.call_action,
                      'dataset_release_create', **payload)

    def test_create_missing_name(self):
        payload = {'dataset': self.dataset['id'],
                   'description': "The best dataset ever, it **rules!**"}

        assert_raises(toolkit.ValidationError, test_helpers.call_action,
                      'dataset_release_create', **payload)

    def test_list(self):
        context = self._get_context(self.org_admin)
        test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        releases = test_helpers.call_action('dataset_release_list',
                                            context,
                                            dataset=self.dataset['id'])
        assert_equals(len(releases), 1)

    def test_list_no_releases(self):
        context = self._get_context(self.org_admin)
        releases = test_helpers.call_action('dataset_release_list',
                                            context,
                                            dataset=self.dataset['id'])
        assert_equals(len(releases), 0)

    def test_list_missing_dataset_id(self):
        payload = {}
        assert_raises(toolkit.ValidationError, test_helpers.call_action,
                      'dataset_release_list', **payload)

    def test_list_not_found(self):
        payload = {'dataset': 'abc123'}
        assert_raises(toolkit.ObjectNotFound, test_helpers.call_action,
                      'dataset_release_list', **payload)

    def test_create_two_releases_for_same_revision(self):
        context = self._get_context(self.org_admin)
        test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="latest",
            description="This points to the latest release")

        releases = test_helpers.call_action('dataset_release_list',
                                            context,
                                            dataset=self.dataset['id'])
        assert_equals(len(releases), 2)

    def test_delete(self):
        context = self._get_context(self.org_admin)
        release = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        test_helpers.call_action('dataset_release_delete', context,
                                 dataset=self.dataset['name'],
                                 release=release['name'])

        releases = test_helpers.call_action('dataset_release_list',
                                            context,
                                            dataset=self.dataset['id'])
        assert_equals(len(releases), 0)

    def test_delete_not_found(self):
        payload = {'dataset': 'abc123', 'release': '1.1'}
        assert_raises(toolkit.ObjectNotFound, test_helpers.call_action,
                      'dataset_release_delete', **payload)

    def test_delete_missing_param(self):
        payload = {}
        assert_raises(toolkit.ValidationError, test_helpers.call_action,
                      'dataset_release_delete', **payload)

    def test_show(self):
        context = self._get_context(self.org_admin)
        release1 = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        release2 = test_helpers.call_action('dataset_release_show', context,
                                            dataset=self.dataset['name'],
                                            release=release1['name'])

        assert_equals(release2, release1)

    def test_show_not_found(self):
        payload = {'dataset': 'abc123', 'release': '1.1'}
        assert_raises(toolkit.ObjectNotFound, test_helpers.call_action,
                      'dataset_release_show', **payload)

    def test_show_missing_param(self):
        payload = {}
        assert_raises(toolkit.ValidationError, test_helpers.call_action,
                      'dataset_release_show', **payload)

    def test_update_last_release(self):
        context = self._get_context(self.org_admin)
        release = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        updated_release = test_helpers.call_action(
            'dataset_release_update',
            context,
            dataset=self.dataset['id'],
            release=release['name'],
            name="0.1.3",
            description="Edited Description"
        )

        assert_equals(release['revision_ref'],
                      updated_release['revision_ref'])
        assert_equals(updated_release['description'],
                      "Edited Description")
        assert_equals(updated_release['name'],
                      "0.1.3")

    def test_update_old_release(self):
        context = self._get_context(self.org_admin)
        old_release = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="1",
            description="This is an old release!")

        test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name="2",
            description="This is a recent release!")

        updated_release = test_helpers.call_action(
            'dataset_release_update',
            context,
            dataset=self.dataset['id'],
            release=old_release['name'],
            name="1.1",
            description="This is an edited old release!"
            )

        assert_equals(old_release['revision_ref'],
                      updated_release['revision_ref'])
        assert_equals(updated_release['description'],
                      "This is an edited old release!")
        assert_equals(updated_release['name'],
                      "1.1")

    def test_update_not_existing_release_raises_error(self):
        context = self._get_context(self.org_admin)

        assert_raises(
            toolkit.ObjectNotFound, test_helpers.call_action,
            'dataset_release_update', context,
            dataset=self.dataset['id'],
            release='abc-123',
            name="0.1.2",
            description='Edited Description'
        )

    def test_revision_diff(self):
        context = self._get_context(self.org_admin)
        release_1 = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name='1',
            description='Release 1')

        test_helpers.call_action(
            'package_patch',
            context,
            id=self.dataset['id'],
            notes='Some changed notes',
        )

        release_2 = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name='2',
            description='Release 2'
        )

        diff = test_helpers.call_action(
            'dataset_release_diff',
            context,
            id=self.dataset['id'],
            revision_ref_1=release_1['name'],
            revision_ref_2=release_2['name'],
        )

        assert_in(
            '-  "notes": "Just another test dataset.", '
            '\n+  "notes": "Some changed notes",',
            diff['diff']
        )

    def test_revision_diff_with_current(self):
        context = self._get_context(self.org_admin)
        release_1 = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=self.dataset['id'],
            name='1',
            description='Release 1')

        test_helpers.call_action(
            'package_patch',
            context,
            id=self.dataset['id'],
            notes='Some changed notes 2',
            license_id='odc-pddl',
        )

        diff = test_helpers.call_action(
            'dataset_release_diff',
            context,
            id=self.dataset['id'],
            revision_ref_1=release_1['name'],
            revision_ref_2='current',
        )

        assert_in(
            '-  "notes": "Just another test dataset.", '
            '\n+  "notes": "Some changed notes 2",',
            diff['diff']
        )

        # TODO: This test fails due to bad logic in the converter
        # assert_in(
        #     '\n-  "license_id": null, '
        #     '\n+  "license_id": "odc-pddl", '
        #     '\n   "license_title": "Open Data Commons Public '
        #     'Domain Dedication and License (PDDL)", '
        #     '\n   "license_url": "http://www.opendefinition.org/'
        #     'licenses/odc-pddl", ',
        #     diff['diff']
        # )


class TestVersioningRevert(MetastoreBackendTestBase):
    """Test cases for reverting a dataset to a revision / release
    """

    def setup(self):

        super(TestVersioningRevert, self).setup()

        self.org_admin = factories.User()
        self.org_admin_name = self.org_admin['name'].encode('ascii')

        self.org_member = factories.User()
        self.org_member_name = self.org_member['name'].encode('ascii')

        self.org = factories.Organization(
            users=[
                {'name': self.org_member['name'], 'capacity': 'member'},
                {'name': self.org_admin['name'], 'capacity': 'admin'},
            ]
        )

        self.dataset = factories.Dataset()

    def test_revert_updates_metadata_fields(self):
        context = self._get_context(self.org_admin)

        initial_dataset = factories.Dataset(
            title='Testing Revert',
            notes='Initial Description',
            maintainer='test_maintainer',
            maintainer_email='test_email@example.com',
            owner_org=self.org['id']
        )

        release = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=initial_dataset['id'],
            name="1.2")

        new_org = factories.Organization(
            users=[
                {'name': self.org_admin['name'], 'capacity': 'admin'},
            ]
        )
        test_helpers.call_action(
            'package_update',
            context,
            name=initial_dataset['name'],
            title='New Title',
            notes='New Notes',
            maintainer='new_test_maintainer',
            maintainer_email='new_test_email@example.com',
            owner_org=new_org['id']
        )

        test_helpers.call_action(
            'dataset_revert',
            context,
            revision_ref=release['name'],
            dataset=release['package_id']
            )

        reverted = test_helpers.call_action(
            'package_show',
            context,
            id=initial_dataset['id']
            )

        assert_equals(reverted['title'], 'Testing Revert')
        assert_equals(reverted['notes'], 'Initial Description')
        assert_equals(reverted['maintainer'], 'test_maintainer')
        assert_equals(reverted['maintainer_email'], 'test_email@example.com')
        assert_equals(reverted['owner_org'], self.org['id'])

    def test_revert_to_revision_id(self):
        context = self._get_context(self.org_admin)

        initial_dataset = factories.Dataset(
            title='Testing Revert',
            notes='Initial Description',
            maintainer='test_maintainer',
            maintainer_email='test_email@example.com',
            owner_org=self.org['id']
        )

        # TODO: For now we use `release_create` and `release_list` to get revision IDs
        # TODO: There is no API to list revisions without creating a release
        # TODO: see https://github.com/datopian/ckanext-versioning/issues/47

        test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=initial_dataset['id'],
            name="1.2")

        releases = test_helpers.call_action(
            'dataset_release_list',
            context,
            dataset=initial_dataset['id'])

        test_helpers.call_action(
            'package_update',
            context,
            name=initial_dataset['name'],
            title='New Title',
            notes='New Notes')

        test_helpers.call_action(
            'dataset_revert',
            context,
            revision_ref=releases[0]['revision_ref'],
            dataset=initial_dataset['id'])

        reverted = test_helpers.call_action(
            'package_show',
            context,
            id=initial_dataset['id'])

        assert_equals(reverted['title'], 'Testing Revert')
        assert_equals(reverted['notes'], 'Initial Description')
        assert_equals(reverted['maintainer'], 'test_maintainer')
        assert_equals(reverted['maintainer_email'], 'test_email@example.com')
        assert_equals(reverted['owner_org'], self.org['id'])

    def test_revert_updates_extras(self):
        context = self._get_context(self.org_admin)

        initial_dataset = factories.Dataset(
            extras=[{'key': u'original extra',
                     'value': u'original value'}])

        release = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=initial_dataset['id'],
            name="1.2")

        test_helpers.call_action(
            'package_update',
            name=initial_dataset['name'],
            extras=[
                {'key': u'new extra', 'value': u'new value'},
                {'key': u'new extra 2', 'value': u'new value 2'}
            ],
        )

        test_helpers.call_action(
            'dataset_revert',
            context,
            dataset=initial_dataset['id'],
            revision_ref=release['name'])

        reverted_dataset = test_helpers.call_action(
            'package_show',
            context,
            id=initial_dataset['id'])

        assert_equals(reverted_dataset['extras'][0]['key'], 'original extra')
        assert_equals(reverted_dataset['extras'][0]['value'],
                      'original value')
        assert_equals(len(reverted_dataset['extras']), 1)

    def test_revert_updates_resources(self):
        context = self._get_context(self.org_admin)

        initial_dataset = factories.Dataset()

        first_resource = factories.Resource(
            name="First Resource",
            package_id=initial_dataset['id']
        )
        initial_dataset['resources'].append(first_resource)

        release = test_helpers.call_action(
            'dataset_release_create',
            context,
            dataset=initial_dataset['id'],
            name="1.2")

        second_resource = factories.Resource(
            name="Second Resource",
            package_id=initial_dataset['id']
        )
        initial_dataset['resources'].append(second_resource)

        test_helpers.call_action(
            'dataset_revert',
            context,
            revision_ref=release['name'],
            dataset=release['package_id']
            )

        reverted_dataset = test_helpers.call_action(
            'package_show',
            context,
            id=initial_dataset['id']
            )

        assert_equals(len(reverted_dataset['resources']), 1)
        assert_equals(
            reverted_dataset['resources'][0]['name'],
            'First Resource')


class TestPackageShowRevision(MetastoreBackendTestBase):
    """Test cases for logic actions
    """

    def setup(self):
        super(TestPackageShowRevision, self).setup()

        self.org_admin = factories.User()
        self.org_admin_name = self.org_admin['name'].encode('ascii')

        self.org_member = factories.User()
        self.org_member_name = self.org_member['name'].encode('ascii')

        self.org = factories.Organization(
            users=[
                {'name': self.org_member['name'], 'capacity': 'member'},
                {'name': self.org_admin['name'], 'capacity': 'admin'},
            ]
        )

        self.dataset = factories.Dataset()
        self.uploaded_resource = factories.Resource(
            package_id=self.dataset['id'],
            url_type='upload',
            url='my-resource.csv'
        )
        self.url_resource = factories.Resource(package_id=self.dataset['id'])

    def test_package_show_revision_gets_current_if_no_revision_id(self):
        context = self._get_context(self.org_admin)

        test_helpers.call_action(
            'package_update',
            context,
            name=self.dataset['name'],
            title='New Title',
            notes='New Notes'
        )

        current_dataset = test_helpers.call_action(
            'package_show',
            context,
            id=self.dataset['id']
            )

        assert_equals(current_dataset['title'], 'New Title')
        # TODO: How do I know that a package is in HEAD? Should we store
        # revision_id in metastore?

    def test_package_show_revision_gets_revision(self):
        context = self._get_context(self.org_admin)
        initial_revision = helpers.get_dataset_current_revision(
            self.dataset['name']
            )

        test_helpers.call_action(
            'package_update',
            context,
            name=self.dataset['name'],
            title='New Title',
            notes='New Notes'
        )

        initial_dataset = test_helpers.call_action(
            'package_show',
            context,
            id=self.dataset['id'],
            revision_ref=initial_revision
            )

        assert_equals(initial_dataset['title'], 'Test Dataset')

    def test_package_show_revision_has_download_url(self):
        context = self._get_context(self.org_admin)
        initial_revision = helpers.get_dataset_current_revision(
            self.dataset['name']
            )

        test_helpers.call_action(
            'package_update',
            context,
            name=self.dataset['name'],
            title='New Title',
            notes='New Notes'
        )

        initial_dataset = test_helpers.call_action(
            'package_show',
            context,
            id=self.dataset['id'],
            revision_ref=initial_revision
            )

        expected = ('http://localhost:5000/dataset/{dataset_id}/resource/'
                    '{resource_id}/download/{filename}?revision_ref={revision_ref}') \
            .format(dataset_id=self.dataset['id'],
                    resource_id=self.uploaded_resource['id'],
                    filename='my-resource.csv',
                    revision_ref=initial_revision)

        assert_equals(initial_dataset['resources'][0]['url'], expected)

    def test_resource_show_revision_has_download_url(self):
        context = self._get_context(self.org_admin)
        initial_revision = helpers.get_dataset_current_revision(
            self.dataset['name']
            )

        test_helpers.call_action(
            'package_update',
            context,
            name=self.dataset['name'],
            title='New Title',
            notes='New Notes'
        )

        initial_resource = test_helpers.call_action(
            'resource_show',
            context,
            id=self.uploaded_resource['id'],
            revision_ref=initial_revision
        )

        expected = ('http://localhost:5000/dataset/{dataset_id}/resource/'
                    '{resource_id}/download/{filename}?revision_ref={revision_ref}')\
            .format(dataset_id=self.dataset['id'],
                    resource_id=self.uploaded_resource['id'],
                    filename='my-resource.csv',
                    revision_ref=initial_revision)

        assert_equals(initial_resource['url'], expected)

    def test_resource_show_revision_external_url_is_unchanged(self):
        context = self._get_context(self.org_admin)
        initial_revision = helpers.get_dataset_current_revision(
            self.dataset['name']
            )

        test_helpers.call_action(
            'package_update',
            context,
            name=self.dataset['name'],
            title='New Title',
            notes='New Notes'
        )

        initial_resource = test_helpers.call_action(
            'resource_show',
            context,
            id=self.url_resource['id'],
            revision_ref=initial_revision
        )

        assert_equals(initial_resource['url'], 'http://link.to.some.data')


class TestDatasetPurge(MetastoreBackendTestBase):

    def setup(self):
        super(TestDatasetPurge, self).setup()

        self.sys_admin = factories.Sysadmin()
        self.org_admin = factories.User()
        self.org = factories.Organization(
            users=[
                {'name': self.org_admin['name'], 'capacity': 'admin'},
            ]
        )

        self.dataset = factories.Dataset(owner_org=self.org['id'])

    def test_dataset_purge_deletes_from_metastore(self):
        context = self._get_context(self.sys_admin)

        test_helpers.call_action(
            'dataset_purge',
            context,
            id=self.dataset['name'],
        )

        backend = helpers.get_metastore_backend()

        with assert_raises(NotFound):
            backend.fetch(self.dataset['name'])

    def test_dataset_purge_works_if_not_in_metastore(self):
        context = self._get_context(self.sys_admin)

        backend = helpers.get_metastore_backend()
        backend.delete(self.dataset['name'])

        test_helpers.call_action(
            'dataset_purge',
            context,
            id=self.dataset['id'],
        )

    def test_dataset_purge_deletes_from_db(self):
        context = self._get_context(self.sys_admin)

        test_helpers.call_action(
            'dataset_purge',
            context,
            id=self.dataset['id'],
        )

        pkg = context['model'].Package.get(self.dataset['id'])
        assert pkg is None, "Package still exists in DB"

    @raises(toolkit.NotAuthorized)
    def test_dataset_purge_not_allowed_to_non_sysadmins(self):
        context = self._get_context(self.org_admin)

        test_helpers.call_action(
            'dataset_purge',
            context,
            id=self.dataset['name'],
        )
