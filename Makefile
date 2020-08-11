# Makefile for ckanext-versioning
PACKAGE_DIR := ckanext/versioning
PACKAGE_NAME := ckanext.versioning

SHELL := bash
PYTHON := python
PIP := pip
PIP_COMPILE := pip-compile
NOSETESTS := nosetests
ISORT := isort
FLAKE8 := flake8
PASTER := paster
DOCKER_COMPOSE := docker-compose
GIT := git

# Find GNU sed in path (on OS X gsed should be preferred)
SED := $(shell which gsed sed | head -n1)

# The `ckan` command line only exists in newer versions of CKAN
CKAN_CLI := $(shell which ckan | head -n1)

TEST_INI_PATH := ./test.ini
SENTINELS := .make-status
TEST_PATH :=
TEST_EXTRA_ARGS :=

PYTHON_VERSION := $(shell $(PYTHON) -c 'import sys; print(sys.version_info[0])')

# CKAN environment variables
CKAN_PATH := ckan
CKAN_REPO_URL := https://github.com/ckan/ckan.git
CKAN_VERSION := ckan-2.8.4
CKAN_CONFIG_FILE := $(CKAN_PATH)/development.ini
CKAN_SITE_URL := http://localhost:5000
POSTGRES_USER := ckan
POSTGRES_PASSWORD := ckan
POSTGRES_DB := ckan
CKAN_SOLR_PASSWORD := ckan
DATASTORE_DB_NAME := datastore
DATASTORE_DB_RO_USER := datastore_ro
DATASTORE_DB_RO_PASSWORD := datastore_ro
CKAN_LOAD_PLUGINS := stats text_view image_view recline_view datastore package_versioning

CKAN_CONFIG_VALUES := \
		ckan.site_url=$(CKAN_SITE_URL) \
		sqlalchemy.url=postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost/$(POSTGRES_DB) \
		ckan.datastore.write_url=postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost/$(DATASTORE_DB_NAME) \
		ckan.datastore.read_url=postgresql://$(DATASTORE_DB_RO_USER):$(DATASTORE_DB_RO_PASSWORD)@localhost/$(DATASTORE_DB_NAME) \
		ckan.plugins='$(CKAN_LOAD_PLUGINS)' \
		ckan.storage_path='%(here)s/storage' \
		solr_url=http://127.0.0.1:8983/solr/ckan \
		ckanext.versioning.backend_type=filesystem \
		ckanext.versioning.backend_config='{"uri":"./metastore"}'

CKAN_TEST_CONFIG_VALUES := \
		sqlalchemy.url=postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost/$(POSTGRES_DB)_test \
		ckan.datastore.write_url=postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@localhost/$(DATASTORE_DB_NAME)_test \
		ckan.datastore.read_url=postgresql://$(DATASTORE_DB_RO_USER):$(DATASTORE_DB_RO_PASSWORD)@localhost/$(DATASTORE_DB_NAME)_test

ifdef WITH_COVERAGE
  COVERAGE_ARG := --with-coverage --cover-package=$(PACKAGE_NAME) --cover-inclusive --cover-erase --cover-tests
else
  COVERAGE_ARG :=
endif

## Install this extension to the current Python environment
install: $(SENTINELS)/install
.PHONY: install

## Set up the extension for development in the current Python environment
develop: $(SENTINELS)/develop
.PHONEY: develop

## Run all tests
test: $(SENTINELS)/tests-passed
.PHONY: test

## Install the right version of CKAN into the virtual environment
ckan-install: $(SENTINELS)/ckan-installed
	@echo "Current CKAN version: $(shell cat $(SENTINELS)/ckan-version)"
.PHONY: ckan-install

## Run CKAN in the local virtual environment
ckan-start: $(SENTINELS)/ckan-installed $(SENTINELS)/install-dev $(CKAN_CONFIG_FILE) | _check_virtualenv
ifdef CKAN_CLI
	$(CKAN_CLI) -c $(CKAN_CONFIG_FILE) db init
	$(CKAN_CLI) -c $(CKAN_CONFIG_FILE) server -r
else
	$(PASTER) --plugin=ckan db init -c $(CKAN_CONFIG_FILE)
	$(PASTER) --plugin=ckan serve --reload --monitor-restart $(CKAN_CONFIG_FILE)
endif
.PHONY: ckan-start

$(CKAN_PATH):
	$(GIT) clone $(CKAN_REPO_URL) $@

$(CKAN_CONFIG_FILE): $(SENTINELS)/ckan-installed $(SENTINELS)/develop | _check_virtualenv
	$(PASTER) make-config --no-interactive ckan $(CKAN_CONFIG_FILE)
ifdef CKAN_CLI
	$(CKAN_CLI) config-tool $(CKAN_CONFIG_FILE) -s DEFAULT debug=true
	$(CKAN_CLI) config-tool $(CKAN_CONFIG_FILE) $(CKAN_CONFIG_VALUES)
else
	$(PASTER) --plugin=ckan config-tool $(CKAN_CONFIG_FILE) -s DEFAULT debug=true
	$(PASTER) --plugin=ckan config-tool $(CKAN_CONFIG_FILE) $(CKAN_CONFIG_VALUES)
endif

.env:
	@___POSTGRES_USER=$(POSTGRES_USER) \
	___POSTGRES_PASSWORD=$(POSTGRES_PASSWORD) \
	___POSTGRES_DB=$(POSTGRES_DB) \
	___CKAN_SOLR_PASSWORD=$(CKAN_SOLR_PASSWORD) \
	___DATASTORE_DB_NAME=$(DATASTORE_DB_NAME) \
	___DATASTORE_DB_USER=$(POSTGRES_USER) \
	___DATASTORE_DB_RO_USER=$(DATASTORE_DB_RO_USER) \
	___DATASTORE_DB_RO_PASSWORD=$(DATASTORE_DB_RO_PASSWORD) \
	env | grep ^___ | $(SED) 's/^___//' > .env
	@cat .env

## Start all Docker services
docker-up: .env
	$(DOCKER_COMPOSE) up -d
	@until $(DOCKER_COMPOSE) exec db pg_isready -U $(POSTGRES_USER); do sleep 1; done
	@sleep 2
	@echo " \
    	CREATE ROLE $(DATASTORE_DB_RO_USER) NOSUPERUSER NOCREATEDB NOCREATEROLE LOGIN PASSWORD '$(DATASTORE_DB_RO_PASSWORD)'; \
    	CREATE DATABASE $(DATASTORE_DB_NAME) OWNER $(POSTGRES_USER) ENCODING 'utf-8'; \
    	CREATE DATABASE $(DATASTORE_DB_NAME)_test OWNER $(POSTGRES_USER) ENCODING 'utf-8'; \
    	CREATE DATABASE $(POSTGRES_DB)_test OWNER $(POSTGRES_USER) ENCODING 'utf-8'; \
    	GRANT ALL PRIVILEGES ON DATABASE $(DATASTORE_DB_NAME) TO $(POSTGRES_USER);  \
    	GRANT ALL PRIVILEGES ON DATABASE $(DATASTORE_DB_NAME)_test TO $(POSTGRES_USER);  \
    	GRANT ALL PRIVILEGES ON DATABASE $(POSTGRES_DB)_test TO $(POSTGRES_USER);  \
    " | $(DOCKER_COMPOSE) exec -T db psql --username "$(POSTGRES_USER)"
.PHONY: docker-up

## Stop all Docker services
docker-down: .env
	$(DOCKER_COMPOSE) down
.PHONY: docker-down

## Stop all Docker services and remove volumes
docker-remove: .env
	$(DOCKER_COMPOSE) down -v
.PHONY: docker-remove

## Initialize the development environment
dev-setup: metastore $(SENTINELS)/ckan-installed $(CKAN_PATH)/who.ini $(CKAN_CONFIG_FILE) $(SENTINELS)/develop | _check_virtualenv
.PHONY: dev-setup

## Start a full development environment
dev-start: dev-setup docker-up ckan-start
.PHONY: dev-start

## Add test users
add-users: | _check_virtualenv
	$(PASTER) --plugin=ckan user add admin password=12345678 email=admin@admin.org -c $(CKAN_CONFIG_FILE)
	$(PASTER) --plugin=ckan sysadmin add admin -c $(CKAN_CONFIG_FILE)

## Create a git tag for the current version
version-tag: | _check_virtualenv
	$(GIT) tag v`$(PYTHON) -c 'import $(PACKAGE_NAME); print($(PACKAGE_NAME).__version__);'`
	$(GIT) push --tags
 .PHONY: version-tag

# Private targets

metastore:
	mkdir -p $@

_check_virtualenv:
	@if [ -z "$(VIRTUAL_ENV)" ]; then \
	  echo "You are not in a virtual environment - activate your virtual environment first"; \
	  exit 1; \
	fi
.PHONY: _check_virtualenv

$(SENTINELS):
	mkdir -p $@

$(SENTINELS)/ckan-version: $(CKAN_PATH) | _check_virtualenv $(SENTINELS)
	$(GIT) -C $(CKAN_PATH) remote update
	$(GIT) -C $(CKAN_PATH) checkout $(CKAN_VERSION)
	if [ -e $(CKAN_PATH)/requirement-setuptools.txt ]; then $(PIP) install -r $(CKAN_PATH)/requirement-setuptools.txt; fi
	if [[ "$(PYTHON_VERSION)" == "2" && -e $(CKAN_PATH)/requirements-py2.txt ]]; then \
	  $(PIP) install -r $(CKAN_PATH)/requirements-py2.txt; \
	else \
	  $(PIP) install -r $(CKAN_PATH)/requirements.txt; \
	fi
	$(PIP) install -r $(CKAN_PATH)/dev-requirements.txt
	$(PIP) install -e $(CKAN_PATH)
	echo "$(CKAN_VERSION)" > $@

$(SENTINELS)/ckan-installed: $(SENTINELS)/ckan-version | $(SENTINELS)
	@if [ "$(shell cat $(SENTINELS)/ckan-version)" != "$(CKAN_VERSION)" ]; then \
	  echo "Switching to CKAN $(CKAN_VERSION)"; \
	  rm $(SENTINELS)/ckan-version; \
	  $(MAKE) $(SENTINELS)/ckan-version; \
	fi
	@touch $@

$(SENTINELS)/test.ini: $(TEST_INI_PATH) $(CKAN_PATH) $(CKAN_PATH)/test-core.ini | $(SENTINELS)
	$(SED) "s@use = config:.*@use = config:$(CKAN_PATH)/test-core.ini@" -i $(TEST_INI_PATH)
ifdef CKAN_CLI
	$(CKAN_CLI) config-tool $(CKAN_PATH)/test-core.ini $(CKAN_CONFIG_VALUES)
	$(CKAN_CLI) config-tool $(CKAN_PATH)/test-core.ini $(CKAN_TEST_CONFIG_VALUES)
else
	$(PASTER) --plugin=ckan config-tool $(CKAN_PATH)/test-core.ini $(CKAN_CONFIG_VALUES) $(CKAN_TEST_CONFIG_VALUES)
endif
	@touch $@

$(SENTINELS)/install: requirements.txt | $(SENTINELS)
	$(PIP) install -r requirements.txt
	@touch $@

$(SENTINELS)/install-dev: requirements.txt setup.py | $(SENTINELS)
	$(PIP) install -r dev-requirements.txt
	$(PIP) install -e .
	@touch $@

$(SENTINELS)/develop: $(SENTINELS)/install $(SENTINELS)/install-dev | $(SENTINELS)
	@touch $@

$(SENTINELS)/test-setup: $(SENTINELS)/develop $(SENTINELS)/test.ini
ifdef CKAN_CLI
	$(CKAN_CLI) -c $(TEST_INI_PATH) db init
else
	$(PASTER) --plugin=ckan db init -c $(TEST_INI_PATH)
endif
	@touch $@

$(SENTINELS)/tests-passed: $(SENTINELS)/test-setup $(shell find $(PACKAGE_DIR) -type f) .flake8 .isort.cfg | $(SENTINELS)
	$(ISORT) -rc -df -c $(PACKAGE_DIR)
	$(FLAKE8) $(PACKAGE_DIR)
	$(NOSETESTS) --ckan -s \
	      --with-pylons=$(TEST_INI_PATH) \
          --nologcapture \
          --with-doctest \
		  $(COVERAGE_ARG) $(TEST_EXTRA_ARGS) $(PACKAGE_DIR)/tests/$(TEST_PATH)
	@touch $@

# Help related variables and targets

GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)
TARGET_MAX_CHAR_NUM := 15

## Show help
help:
	@echo ''
	@echo 'Usage:'
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\-\_0-9]+:/ { \
	  helpMessage = match(lastLine, /^## (.*)/); \
	  if (helpMessage) { \
	    helpCommand = substr($$1, 0, index($$1, ":")-1); \
	    helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
	    printf "  ${YELLOW}%-$(TARGET_MAX_CHAR_NUM)s${RESET} ${GREEN}%s${RESET}\n", helpCommand, helpMessage; \
	  } \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST)
