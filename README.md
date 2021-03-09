<div align="center">
  
# DEPRECATED. See https://github.com/datopian/ckanext-versions

# Data Versioning for CKAN

</div>


CKAN + data versioning 🚀. This CKAN extension adds a full data versioning capability to [CKAN][] including:

* Metadata and data is **revisioned** so that all updates create new revision and old versions of the metadata and data are accessible
* Create and manage **releases** - named labels plus a description for a specific revision of a dataset, e.g. "v1.0". 
  These are similar in concept to VCS tags. 
* Diffs, reverting etc

For more background see https://tech.datopian.com/versioning/

[CKAN]: https://ckan.org/

## Requirements

ckanext-verisoning requires CKAN 2.8.4 or a newer version of CKAN 2.8. 
It may work with CKAN 2.9 as well but this is currently not tested.

## Installation

To install ckanext-versioning:

1. Activate your CKAN virtual environment, for example:

       . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-versioning Python package into your virtual environment:

       pip install ckanext-versioning

3. Add ``package_versioning`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

       sudo service apache2 reload

## Configuration settings
The following CKAN INI configuration settings are required for this plugin
to operate properly:

### `ckanext.versioning.backend_type`

Should be set to a valid [metastore-lib backend type][1], for example:

    ckanext.versioning.backend_type = filesystem

### `ckanext.versioning.backend_config`

Should be a Python dictionary containing configuration options to pass
to the metastore-lib backend factory. The specific configuration
options accepted for each backend [are documented here][1].

For example, for the `filesystem` backend one can use:

    ckanext.versioning.backend_config = {"uri":"./metastore"}

To set the metadata storage path to `./metastore` on the local file system. 

## API Actions

This extension exposes a number of new API actions to manage and use
dataset revisions and releases.

The HTTP method is GET for list / show actions and POST for create / delete
actions.

You will need to also pass in authentication information such as cookies or
tokens - you should consult the `CKAN API Guide
<https://docs.ckan.org/en/2.8/api/>`_ for details.

The following ``curl`` examples all assume the ``$API_KEY`` environment
variable is set and contains a valid CKAN API key, belonging to a user with
sufficient privileges; Output is indented and cleaned up for readability.

### `dataset_release_list`

List releases for a dataset.

**HTTP Method**: ``GET``

**Query Parameters**:

* ``dataset=<dataset_id>`` - The UUID or unique name of the dataset (required)

**Example**:

```
$ curl -H "Authorization: $API_KEY" \
  https://ckan.example.com/api/3/action/dataset_release_list?dataset=my-awesome-dataset

{
  "help": "http://ckan.example.com/api/3/action/help_show?name=dataset_release_list",
  "success": true,
  "result": [
    {
      "id": "5942ab7a-67cb-426c-ad99-dd4519530bc7",
      "package_id": "3b5a4f83-8770-4e8c-9630-c8abf6aa20f4",
      "package_revision_id": "7316fb6c-07e7-43b7-ade8-ac26c5693e6d",
      "name": "Version 1.2",
      "description": "Updated to include latest study results",
      "creator_user_id": "70587302-6a93-4c0a-bb3e-4d64c0b7c213",
      "created": "2019-10-27 15:29:53.452833"
    },
    {
      "id": "87d6f58a-a899-4f2d-88a4-c22e9e1e5dfb",
      "package_id": "3b5a4f83-8770-4e8c-9630-c8abf6aa20f4",
      "package_revision_id": "1b9fc99e-8e32-449e-85c2-24c893d9761e",
      "name": "Corrected for inflation",
      "description": "With Avi Bitter",
      "creator_user_id": "70587302-6a93-4c0a-bb3e-4d64c0b7c213",
      "created": "2019-10-27 15:29:16.070904"
    },
    {
      "id": "3e5601e2-1b39-43b6-b197-8040cc10036e",
      "package_id": "3b5a4f83-8770-4e8c-9630-c8abf6aa20f4",
      "package_revision_id": "e30ba6a8-d453-4395-8ee5-3aa2f1ca9e1f",
      "name": "Version 1.0",
      "description": "Added another resource with index of countries",
      "creator_user_id": "70587302-6a93-4c0a-bb3e-4d64c0b7c213",
      "created": "2019-10-27 15:24:25.248153"
    }
  ]
}
```

### `dataset_release_show`

Show info about a specific dataset release.

Note that this will show the release information - not the dataset metadata or
data (see `package_show_release`_)

**HTTP Method**: ``GET``

**Query Parameters**:

 * ``id=<dataset_release_id>`` - The UUID of the release to show (required)

**Example**:


```
$ curl -H "Authorization: $API_KEY" \
  https://ckan.example.com/api/3/action/dataset_release_show?id=5942ab7a-67cb-426c-ad99-dd4519530bc7

{
  "help": "http://ckan.example.com/api/3/action/help_show?name=dataset_release_show",
  "success": true,
  "result": {
    "id": "5942ab7a-67cb-426c-ad99-dd4519530bc7",
    "package_id": "3b5a4f83-8770-4e8c-9630-c8abf6aa20f4",
    "package_revision_id": "7316fb6c-07e7-43b7-ade8-ac26c5693e6d",
    "name": "Version 1.2",
    "description": "Updated to include latest study results",
    "creator_user_id": "70587302-6a93-4c0a-bb3e-4d64c0b7c213",
    "created": "2019-10-27 15:29:53.452833"
  }
}
```

### `dataset_release_create`

Create a new release for the specified dataset *current* revision. You are
required to specify a name for the release, and can optionally specify a
description.

**HTTP Method**: ``POST``

**JSON Parameters**:

 * ``dataset=<dataset_id>`` - UUID or name of the dataset (required, string)
 * ``name``=<release_name>`` - Name for the release. Release names must be
   unique per dataset (required, string)
 * ``description=<description>`` - Long description for the release; Can be
   markdown formatted (optional, string)

**Example**:

```
$ curl -H "Authorization: $API_KEY" \
       -H "Content-type: application/json" \
       -X POST \
       https://ckan.example.com/api/3/action/dataset_release_create \
       -d '{"dataset":"3b5a4f83-8770-4e8c-9630-c8abf6aa20f4", "name": "Version 1.3", "description": "With extra Awesome Sauce"}'

{
  "help": "https://ckan.example.com/api/3/action/help_show?name=dataset_release_create",
  "success": true,
  "result": {
    "id": "e1a77b78-dfaf-4c05-a261-ff01af10d601",
    "package_id": "3b5a4f83-8770-4e8c-9630-c8abf6aa20f4",
    "package_revision_id": "96ad6e02-99cf-4598-ab10-ea80e864e505",
    "name": "Version 1.3",
    "description": "With extra Awesome Sauce",
    "creator_user_id": "70587302-6a93-4c0a-bb3e-4d64c0b7c213",
    "created": "2019-10-28 08:14:01.953796"
  }
}
```

### `dataset_release_delete`

Delete a dataset release. This does not delete the dataset revision, just the
named release pointing to it.

**HTTP Method**: ``POST``

**JSON Parameters**:

 * ``id=<dataset_release_id>`` - The UUID of the release to delete (required,
   string)

**Example**::

```
$ curl -H "Authorization: $API_KEY" \
       -H "Content-type: application/json" \
       -X POST \
       https://ckan.example.com/api/3/action/dataset_release_delete \
       -d '{"id":"e1a77b78-dfaf-4c05-a261-ff01af10d601"}'

{
  "help": "https://ckan.example.com/api/3/action/help_show?name=dataset_release_delete",
  "success": true,
  "result": null
}
```

### `package_show_release`

Show a dataset (AKA package) in a given release. This is identical to the
built-in ``package_show`` action, but shows dataset metadata for a given
release, and adds some versioning related metadata.

This is useful if you've used ``dataset_release_list`` to get all
named releases for a dataset, and now want to show that dataset in a specific
release.

If ``release_id`` is not specified, the latet release of the dataset will be
returned, but will include a list of releases for the dataset.

**HTTP Method**: ``GET``

**Query Parameters**:

 * ``id=<dataset_id>`` - The name or UUID of the dataset (required)
 * ``release_id=<release_id>`` - A release name to show (optional)

**Examples**:

Fetching dataset metadata in a specified release:

```
$ curl -H "Authorization: $API_KEY" \
       'https://ckan.example.com/api/3/action/package_show_release?id=3b5a4f83-8770-4e8c-9630-c8abf6aa20f4&release_id=5942ab7a-67cb-426c-ad99-dd4519530bc7'

{
  "help": "https://ckan.example.com/api/3/action/help_show?name=package_show_release",
  "success": true,
  "result": {
    "maintainer": "Bob Paulson",
    "relationships_as_object": [],
    "private": true,
    "maintainer_email": "",
    "num_releases": 2,

    "release_metadata": {
      "id": "5942ab7a-67cb-426c-ad99-dd4519530bc7",
      "package_id": "3b5a4f83-8770-4e8c-9630-c8abf6aa20f4",
      "package_revision_id": "7316fb6c-07e7-43b7-ade8-ac26c5693e6d",
      "name": "Version 1.2",
      "description": "Without Avi Bitter",
      "creator_user_id": "70587302-6a93-4c0a-bb3e-4d64c0b7c213",
      "created": "2019-10-27 15:29:53.452833"
    },

    "id": "3b5a4f83-8770-4e8c-9630-c8abf6aa20f4",
    "metadata_created": "2019-10-27T15:23:50.612130",
    "owner_org": "68f832f7-5952-4cac-8803-4af55c021ccd",
    "metadata_modified": "2019-10-27T20:14:42.564886",
    "author": "Joe Bloggs",
    "author_email": "",
    "state": "active",
    "version": "1.0",
    "type": "dataset",
    "resources": [
      {
        "cache_last_updated": null,
        "cache_url": null,
        "mimetype_inner": null,
        /// ... standard resource attributes ...
      }
    ],
    "num_resources": 1,

    /// ... more standard dataset attributes ...
  }
}
```

Note the ``release_metadata``, which is only included with dataset metadata if
the ``release_id`` parameter was provided.

Fetching the current revision of dataset metadata in a specified release:

```
{
  "help": "https://ckan.example.com/api/3/action/help_show?name=package_show_release",
  "success": true,
  "result": {
    "license_title": "Green",
    "relationships_as_object": [],
    "private": true,
    "id": "3b5a4f83-8770-4e8c-9630-c8abf6aa20f4",
    "metadata_created": "2019-10-27T15:23:50.612130",
    "metadata_modified": "2019-10-27T20:14:42.564886",
    "author": "Joe Bloggs",
    "author_email": "",
    "state": "active",
    "release": "1.0",
    "creator_user_id": "70587302-6a93-4c0a-bb3e-4d64c0b7c213",
    "type": "dataset",
    "resources": [
      {
        "mimetype": "text/csv",
        "cache_url": null,
        "hash": "",
        "description": "",
        "name": "https://data.example.com/dataset/287f7e34-7675-49a9-90bd-7c6a8b55698e/resource.csv",
        "format": "CSV",
        /// ... standard resource attributes ...
      }
    ],
    "num_resources": 1,
    "releases": [
      {
        "vocabulary_id": null,
        "state": "active",
        "display_name": "bar",
        "id": "686198e2-7b9c-4986-bb19-3cf74cfe2552",
        "name": "bar"
      },
      {
        "vocabulary_id": null,
        "state": "active",
        "display_name": "foo",
        "id": "82259424-aec6-428c-a682-0b3f6b8ee67d",
        "name": "foo"
      }
    ],

    "releases": [
      {
        "id": "5942ab7a-67cb-426c-ad99-dd4519530bc7",
        "package_id": "3b5a4f83-8770-4e8c-9630-c8abf6aa20f4",
        "package_revision_id": "7316fb6c-07e7-43b7-ade8-ac26c5693e6d",
        "name": "Version 1.2",
        "description": "Fixed some inaccuracies in data",
        "creator_user_id": "70587302-6a93-4c0a-bb3e-4d64c0b7c213",
        "created": "2019-10-27 15:29:53.452833"
      },
      {
        "id": "87d6f58a-a899-4f2d-88a4-c22e9e1e5dfb",
        "package_id": "3b5a4f83-8770-4e8c-9630-c8abf6aa20f4",
        "package_revision_id": "1b9fc99e-8e32-449e-85c2-24c893d9761e",
        "name": "version 1.1",
        "description": "Adjusted for country-specific inflation",
        "creator_user_id": "70587302-6a93-4c0a-bb3e-4d64c0b7c213",
        "created": "2019-10-27 15:29:16.070904"
      }
    ],

    /// ... more standard dataset attributes ...
  }
}
```


Note the ``releases`` list, only included when showing the latest
dataset release via ``package_show_release``.


## Config Settings

This extension does not provide any additional configuration settings.

## Development Installation

To install ckanext-versioning for development, activate your CKAN virtualenv and
do:

```
git clone https://github.com/datopian/ckanext-versioning.git
cd ckanext-versioning
python setup.py develop
pip install -r dev-requirements.txt
```

## Running the Tests

To run the tests, do:

```
make test
make test TEST_PATH=test_file.py # to run all the tests of a specific file.
make test TEST_PATH=test_file.py:Class # to run all the tests of a specific Class.
make test TEST_PATH=test_file.py:Class.test_name # to execute a specific test.
```

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run:

    make test coverage

Note that for tests to run properly, you need to have this extension installed
in an environment that has CKAN installed in it, and configured to access a
local PostgreSQL and Solr instances.

You can specify the path to your local CKAN installation by adding:

    make test CKAN_PATH=../../src/ckan/

For example.

In addition, the following environment variables are useful when testing:

    CKAN_SQLALCHEMY_URL=postgres://ckan:ckan@my-postgres-db/ckan_test
    CKAN_SOLR_URL=http://my-solr-instance:8983/solr/ckan

[1]: https://metastore-lib.readthedocs.io/en/latest/backends/index.html#id1
