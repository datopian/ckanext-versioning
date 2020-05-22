"""Tests for plugin.py."""
import ckanext.versioning.plugin as plugin


def test_plugin():
    """This is here just as a sanity test
    """
    p = plugin.VersioningPlugin()
    assert p
