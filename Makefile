# Makefile for ckanext-versioning

PACKAGE_DIR := ckanext/versioning

SHELL := bash
PIP := pip
ISORT := isort
FLAKE8 := flake8
NOSETESTS := nosetests
SED := sed
PASTER := paster

TEST_INI_PATH := ./test.ini
CKAN_PATH := ../../src/ckan
TEST_PATH :=

prepare-config:
	$(SED) "s@use = config:.*@use = config:$(CKAN_PATH)/test-core.ini@" -i $(TEST_INI_PATH)

test: prepare-config
	$(PIP) install -r dev-requirements.txt
	$(ISORT) -rc -df -c $(PACKAGE_DIR)
	$(FLAKE8) $(PACKAGE_DIR)
	$(PASTER) --plugin=ckan db init -c $(CKAN_PATH)/test-core.ini
	$(NOSETESTS) --ckan \
	      --with-pylons=$(TEST_INI_PATH) \
          --nologcapture \
          --with-doctest \
		  ckanext/versioning/tests/$(TEST_PATH)

coverage: prepare-config test
	$(NOSETESTS) --ckan \
	      --with-pylons=$(TEST_INI_PATH) \
          --nologcapture \
		  --with-coverage \
          --cover-package=ckanext.versioning \
          --cover-inclusive \
          --cover-erase \
          --cover-tests
