# Makefile for ckanext-versioning

PACKAGE_DIR := ckanext/versioning

SHELL := bash
PIP := pip
ISORT := isort
FLAKE8 := flake8
NOSETESTS := nosetests
PASTER := paster
DOCKER_COMPOSE := docker-compose

# Find GNU sed in path (on OS X gsed should be preferred)
SED := $(shell which gsed sed | head -n1)

TEST_INI_PATH := ./test.ini
CKAN_PATH := ../ckan
TEST_PATH :=

# These are used in creating .env file and ckan config
CKAN_SITE_URL := http://localhost:5000
POSTGRES_USER := ckan
POSTGRES_PASSWORD := ckan
POSTGRES_DB := ckan
CKAN_SOLR_PASSWORD := ckan
DATASTORE_DB_NAME := datastore
DATASTORE_DB_RO_USER := datastore_ro
DATASTORE_DB_RO_PASSWORD := datastore_ro

prepare-config:
	$(SED) "s@use = config:.*@use = config:$(CKAN_PATH)/test-core.ini@" -i $(TEST_INI_PATH)

test: prepare-config
	$(PIP) install -r dev-requirements.txt
	$(ISORT) -rc -df -c $(PACKAGE_DIR)
	$(FLAKE8) $(PACKAGE_DIR)
	$(PASTER) --plugin=ckan db init -c $(CKAN_PATH)/test-core.ini
	$(NOSETESTS) --ckan -s \
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
