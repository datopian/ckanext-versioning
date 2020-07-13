"""Tests for plugin.py."""
import ckanext.versioning.plugin as plugin


def test_package_versioning_plugin():
    """This is here just as a sanity test
    """
    p = plugin.PackageVersioningPlugin()
    assert p
