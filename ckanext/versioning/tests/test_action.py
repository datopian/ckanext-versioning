from ckan.plugins import toolkit
from ckan.tests import factories
from ckan.tests import helpers as test_helpers
from nose.tools import assert_equals, assert_in, assert_raises

from ckanext.versioning.common import get_metastore_backend
from ckanext.versioning.logic import helpers
from ckanext.versioning.tests import MetastoreBackendTestBase


class TestVersionsActions(MetastoreBackendTestBase):
    """Test cases for logic actions
    """

    def setup(self):
        super(TestVersionsActions, self).setup()

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

    def test_create_tag(self):
        """Test basic dataset version creation
        """
        context = self._get_context(self.org_admin)
        version = test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        revision = helpers.get_dataset_current_revision(self.dataset['name'])

        assert_equals(version['package_id'], self.dataset['name'])
        assert_equals(version['revision_ref'],
                      revision)
        assert_equals(version['description'],
                      "The best dataset ever, it **rules!**")
        assert_equals(version['author'], self.org_admin['name'])
        assert_equals(version['author_email'], self.org_admin['email'])

    def test_create_tag_name_already_exists(self):
        """Test that creating a version with an existing name for the same
        dataset raises an error
        """
        context = self._get_context(self.org_admin)
        test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name="HEAD",
            description="The best dataset ever, it **rules!**")

        assert_raises(toolkit.ValidationError, test_helpers.call_action,
                      'dataset_tag_create', context,
                      dataset=self.dataset['id'],
                      name="HEAD",
                      description="This is also a good version")

    def test_create_dataset_not_found(self):
        payload = {'dataset': 'abc123',
                   'name': "Version 0.1.2"}

        assert_raises(toolkit.ObjectNotFound, test_helpers.call_action,
                      'dataset_tag_create', **payload)

    def test_create_missing_name(self):
        payload = {'dataset': self.dataset['id'],
                   'description': "The best dataset ever, it **rules!**"}

        assert_raises(toolkit.ValidationError, test_helpers.call_action,
                      'dataset_tag_create', **payload)

    def test_list(self):
        context = self._get_context(self.org_admin)
        test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        versions = test_helpers.call_action('dataset_tag_list',
                                            context,
                                            dataset=self.dataset['id'])
        assert_equals(len(versions), 1)

    def test_list_no_versions(self):
        context = self._get_context(self.org_admin)
        versions = test_helpers.call_action('dataset_tag_list',
                                            context,
                                            dataset=self.dataset['id'])
        assert_equals(len(versions), 0)

    def test_list_missing_dataset_id(self):
        payload = {}
        assert_raises(toolkit.ValidationError, test_helpers.call_action,
                      'dataset_tag_list', **payload)

    def test_list_not_found(self):
        payload = {'dataset': 'abc123'}
        assert_raises(toolkit.ObjectNotFound, test_helpers.call_action,
                      'dataset_tag_list', **payload)

    def test_create_two_versions_for_same_revision(self):
        context = self._get_context(self.org_admin)
        test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name="latest",
            description="This points to the latest version")

        versions = test_helpers.call_action('dataset_tag_list',
                                            context,
                                            dataset=self.dataset['id'])
        assert_equals(len(versions), 2)

    def test_delete(self):
        context = self._get_context(self.org_admin)
        version = test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        test_helpers.call_action('dataset_tag_delete', context,
                                 dataset=self.dataset['name'],
                                 tag = version['name'])

        versions = test_helpers.call_action('dataset_tag_list',
                                            context,
                                            dataset=self.dataset['id'])
        assert_equals(len(versions), 0)

    def test_delete_not_found(self):
        payload = {'dataset': 'abc123', 'tag': '1.1'}
        assert_raises(toolkit.ObjectNotFound, test_helpers.call_action,
                      'dataset_tag_delete', **payload)

    def test_delete_missing_param(self):
        payload = {}
        assert_raises(toolkit.ValidationError, test_helpers.call_action,
                      'dataset_tag_delete', **payload)

    def test_show(self):
        context = self._get_context(self.org_admin)
        version1 = test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        version2 = test_helpers.call_action('dataset_tag_show', context,
                                            dataset=self.dataset['name'],
                                            tag=version1['name'])

        assert_equals(version2, version1)

    def test_show_not_found(self):
        payload = {'dataset': 'abc123', 'tag': '1.1'}
        assert_raises(toolkit.ObjectNotFound, test_helpers.call_action,
                      'dataset_tag_show', **payload)

    def test_show_missing_param(self):
        payload = {}
        assert_raises(toolkit.ValidationError, test_helpers.call_action,
                      'dataset_tag_show', **payload)

    def test_update_last_version(self):
        context = self._get_context(self.org_admin)
        version = test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name="0.1.2",
            description="The best dataset ever, it **rules!**")

        updated_version = test_helpers.call_action(
            'dataset_tag_update',
            context,
            dataset=self.dataset['id'],
            tag=version['name'],
            name="0.1.3",
            description="Edited Description"
        )

        assert_equals(version['revision_ref'],
                      updated_version['revision_ref'])
        assert_equals(updated_version['description'],
                      "Edited Description")
        assert_equals(updated_version['name'],
                      "0.1.3")

    def test_update_old_version(self):
        context = self._get_context(self.org_admin)
        old_version = test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name="1",
            description="This is an old version!")

        test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name="2",
            description="This is a recent version!")

        updated_version = test_helpers.call_action(
            'dataset_tag_update',
            context,
            dataset=self.dataset['id'],
            tag=old_version['name'],
            name="1.1",
            description="This is an edited old version!"
            )

        assert_equals(old_version['revision_ref'],
                      updated_version['revision_ref'])
        assert_equals(updated_version['description'],
                      "This is an edited old version!")
        assert_equals(updated_version['name'],
                      "1.1")

    def test_update_not_existing_version_raises_error(self):
        context = self._get_context(self.org_admin)

        assert_raises(
            toolkit.ObjectNotFound, test_helpers.call_action,
            'dataset_tag_update', context,
            dataset=self.dataset['id'],
            tag='abc-123',
            name="0.1.2",
            description='Edited Description'
        )

    def test_versions_diff(self):
        context = self._get_context(self.org_admin)
        version_1 = test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name='1',
            description='Version 1')

        test_helpers.call_action(
            'package_patch',
            context,
            id=self.dataset['id'],
            notes='Some changed notes',
        )

        version_2 = test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name='2',
            description='Version 2'
        )

        diff = test_helpers.call_action(
            'dataset_versions_diff',
            context,
            id=self.dataset['id'],
            tag_1=version_1['name'],
            tag_2=version_2['name'],
        )

        assert_in(
            '-  "notes": "Just another test dataset.", '
            '\n+  "notes": "Some changed notes",',
            diff['diff']
        )

    def test_versions_diff_with_current(self):
        context = self._get_context(self.org_admin)
        version_1 = test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=self.dataset['id'],
            name='1',
            description='Version 1')

        test_helpers.call_action(
            'package_patch',
            context,
            id=self.dataset['id'],
            notes='Some changed notes 2',
            license_id='odc-pddl',
        )

        diff = test_helpers.call_action(
            'dataset_versions_diff',
            context,
            id=self.dataset['id'],
            tag_1=version_1['name'],
            tag_2='current',
        )

        assert_in(
            '-  "notes": "Just another test dataset.", '
            '\n+  "notes": "Some changed notes 2",',
            diff['diff']
        )

        # TODO: This test fails due to bad logic in the convertor
        # assert_in(
        #     '\n-  "license_id": null, '
        #     '\n+  "license_id": "odc-pddl", '
        #     '\n   "license_title": "Open Data Commons Public '
        #     'Domain Dedication and License (PDDL)", '
        #     '\n   "license_url": "http://www.opendefinition.org/'
        #     'licenses/odc-pddl", ',
        #     diff['diff']
        # )


class TestVersionsPromote(MetastoreBackendTestBase):
    """Test cases for promoting a dataset version to latest
    """

    def setup(self):

        super(TestVersionsPromote, self).setup()

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

    def test_promote_version_updates_metadata_fields(self):
        context = self._get_context(self.org_admin)

        initial_dataset = factories.Dataset(
            title='Testing Promote',
            notes='Initial Description',
            maintainer='test_maintainer',
            maintainer_email='test_email@example.com',
            owner_org=self.org['id']
        )

        version = test_helpers.call_action(
            'dataset_tag_create',
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
            'dataset_tag_promote',
            context,
            tag=version['name'],
            dataset=version['package_id']
            )

        promoted_dataset = test_helpers.call_action(
            'package_show',
            context,
            id=initial_dataset['id']
            )

        assert_equals(promoted_dataset['title'], 'Testing Promote')
        assert_equals(promoted_dataset['notes'], 'Initial Description')
        assert_equals(promoted_dataset['maintainer'], 'test_maintainer')
        assert_equals(
            promoted_dataset['maintainer_email'], 'test_email@example.com')
        assert_equals(promoted_dataset['owner_org'], self.org['id'])

    # TODO: Fix this test when the convert logic is ok
    # def test_promote_version_updates_extras(self):
    #     context = self._get_context(self.org_admin)

    #     initial_dataset = factories.Dataset(
    #         extras=[{'key': u'original extra',
    #                  'value': u'"original value"'}])

    #     version = test_helpers.call_action(
    #         'dataset_tag_create',
    #         context,
    #         dataset=initial_dataset['id'],
    #         name="1.2")

    #     test_helpers.call_action(
    #         'package_update',
    #         name=initial_dataset['name'],
    #         extras=[
    #             {'key': u'new extra', 'value': u'"new value"'},
    #             {'key': u'new extra 2', 'value': u'"new value 2"'}
    #             ],
    #     )

    #     test_helpers.call_action(
    #         'dataset_tag_promote',
    #         context,
    #         version=version['id']
    #         )

    #     promoted_dataset = test_helpers.call_action(
    #         'package_show',
    #         context,
    #         id=initial_dataset['id']
    #         )

    #     assert_equals(
    #         promoted_dataset['extras'][0]['key'],
    #         'original extra')
    #     assert_equals(
    #         promoted_dataset['extras'][0]['value'],
    #         '"original value"')
    #     assert_equals(len(promoted_dataset['extras']), 1)

    def test_promote_version_updates_resources(self):
        context = self._get_context(self.org_admin)

        initial_dataset = factories.Dataset()

        first_resource = factories.Resource(
            name="First Resource",
            package_id=initial_dataset['id']
        )
        initial_dataset['resources'].append(first_resource)

        version = test_helpers.call_action(
            'dataset_tag_create',
            context,
            dataset=initial_dataset['id'],
            name="1.2")

        second_resource = factories.Resource(
            name="Second Resource",
            package_id=initial_dataset['id']
        )
        initial_dataset['resources'].append(second_resource)

        test_helpers.call_action(
            'dataset_tag_promote',
            context,
            tag=version['name'],
            dataset=version['package_id']
            )

        promoted_dataset = test_helpers.call_action(
            'package_show',
            context,
            id=initial_dataset['id']
            )

        assert_equals(len(promoted_dataset['resources']), 1)
        assert_equals(
            promoted_dataset['resources'][0]['name'],
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
            tag=initial_revision
            )

        assert_equals(initial_dataset['title'], 'Test Dataset')
