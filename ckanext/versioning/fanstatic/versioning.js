/* API for ckanext-versioning */

"use strict";

ckan.module('dataset_versioning_controls', function ($) {

    return {

        _apiBaseUrl: null,
        _packageId: null,
        _packageUrl: null,

        initialize: function ()
        {
            $.proxyAll(this, /_on/);
            this._apiBaseUrl = this.options.apiUrl;
            this._packageId = this.options.packageId;
            this._packageUrl = this.options.packageUrl;
            this._linkResources = this.options.linkResources;
            this._release = this.options.release || null;

            if(this._linkResources){
                this.$(".modal-body").append(
                    ['<div class="form-group">',
                    '<span>',
                    '<i class="fa fa-info-circle"></i>',
                    'This dataset contains resources that are links to external systems. The URL to the file will be versioned but we cannot guarantee that the data itself will remain the same over time. If the content of the external URL changes (while the URL doesn\'t), you will no longer have the ability to get the old version of the data.',
                    '</span>',
                    '</div>'].join('\n')
                );
            };

            this.$('.delete-release-btn').on('click', this._onDelete);
            this.$('.create-release-form').on('submit', this._onCreate);
            this.$('.update-release-form').on('submit', this._onUpdate);
            this.$('.revert-to-btn').on('click', this._onRevert);

            $(document).ready(this._onDocumentReady);
        },

        _onDocumentReady: function ()
        {
            this._loadReleaseList(this._packageId);
        },

        _onDelete: function (evt)
        {
            let dataset = $(evt.target).data('dataset');
            let release = $(evt.target).data('release-name');
            release = String(release);

            if (confirm("Are you sure you want to delete the release \"" + release + "\" of this dataset?")) {
                return this._delete(release, dataset);
            }
        },

        _onCreate: function (evt)
        {
            let releaseName = evt.target.querySelector("input[name=release_name]").value.trim();
            let description = evt.target.querySelector("textarea[name=description]").value.trim();
            evt.preventDefault();
            return this._create(this._packageId, releaseName, description);
        },

        _onUpdate: function(evt)
        {
            let releaseName = evt.target.querySelector("input[name=release_name]").value.trim();
            let description = evt.target.querySelector("textarea[name=description]").value.trim();

            evt.preventDefault();
            return this._update(this._packageId, this._release, releaseName, description);
        },

        _onRevert: function(evt)
        {
            let dataset = $(evt.target).data('dataset');
            let revision_ref = $(evt.target).data('revision-ref');
            revision_ref = String(revision_ref);

            if (confirm(
                "Are you sure you want to revert this dataset to the older release \"" + revision_ref + "\"?\n\n" +
                "Note that when doing this the current state will be lost. If you want to preserve it, please cancel and create a release for it first.")) {
                return this._revert(revision_ref, dataset);
            }
        },

        _apiPost: function (action, params)
        {
            let url = this._apiBaseUrl + action;
            return fetch(url, {
                method: 'POST',
                body: JSON.stringify(params),
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        },

        _loadReleaseList: function (datasetId) {
            let params = new URLSearchParams({"dataset": datasetId});
            let url = this._apiBaseUrl + 'dataset_release_list?' + params;
            let that = this;

            fetch(url).then(function(response) {
                if (response.status !== 200) {
                    console.error("Failed to fetch list of releases, got HTTP " + response.status);
                } else {
                    response.json().then(function(payload) {
                        that._renderReleaseList(payload.result);
                    }).catch(function(e) {
                        console.error("Failed rendering list of releases: " + e);
                    });
                }
            }).catch(function(e) {
                console.error("Error fetching list of releases: " + e);
            });
        },

        _renderReleaseList: function (releases) {
            const loader = $('#release-list .release-list__loading');
            const table = $('#release-list .release-list__list');
            const btnCompareRelease = $('#btnCompareRelease');
            const noReleasesMessage = $('#release-list .release-list__no-releases');
            const releaseRowTemplate = $('tbody tr', table)[0];
            const releaseHrefTemplate = $('.release-list__release-name a', releaseRowTemplate).attr('href');

            loader.hide();

            if (releases.length < 1) {
                noReleasesMessage.show();
                return;
            }

            $('tbody', table).empty();
            for (let i = 0; i < releases.length; i++) {
                let release = releases[i];
                let row = $(releaseRowTemplate).clone();
                table.append(row);
                $('.release-list__release-name a', row).attr('href', releaseHrefTemplate.replace('__REVISION_REF__', release.name));
                $('.release-list__release-name a', row).text(release.name);
                $('.release-list__release-description', row).text(release.description);

                let datetime = $('<span class="automatic-local-datetime"/>');
                datetime.text(moment(release.created).format('LL, LT ([UTC]Z)'));
                datetime.data('datetime', release.created);
                $('.release-list__release-timestamp', row).append(datetime);
            }

            table.show();
            btnCompareRelease.show();
        },

        _delete: function (release, dataset) {
            const action = 'dataset_release_delete';
            let params = {
                release: release,
                dataset: dataset
            };
            let that = this;
            this._apiPost(action, params)
                .then(function (response) {
                    if (response.status !== 200) {
                        that._show_error_message(response, 'deleting')
                    } else {
                        location.href = this._packageUrl;
                    }
                }.bind(this));
        },

        _create: function (datasetId, releaseName, description) {
            const action = 'dataset_release_create';
            let params = {
                dataset: datasetId,
                name: releaseName,
                description: description
            };
            let that = this;
            this._apiPost(action, params)
                .then(function (response) {
                    if (response.status !== 200) {
                        that._show_error_message(response, 'creating')
                    } else {
                        location.reload();
                    }
                });
        },

        _update: function (datasetId, release, releaseName, description) {
            const action = 'dataset_release_update';
            let params = {
                dataset: datasetId,
                release: release,
                name: releaseName,
                description: description
            };
            let that = this;
            this._apiPost(action, params)
                .then(function (response) {
                    if (response.status !== 200) {
                        that._show_error_message(response, 'updating')
                    } else {
                        location.reload();
                    }
                });
        },

        _revert: function (revision_ref, dataset) {
            const action = 'dataset_revert';
            const body = $('html,body');
            let params = {
                revision_ref: revision_ref,
                dataset: dataset
            };
            let that = this;
            this._apiPost(action, params)
                .then(function (response) {
                    if (response.status !== 200) {
                        that._show_error_message(response, 'reverting')
                    } else {
                        that.sandbox.notify(
                            'Success: ',
                            'Dataset reverted successfully. You can now go back to the main dataset page to see the changes.',
                            'success'
                            );
                        body.scrollTop(0);
                    }
                }.bind(this));
        },

        _show_error_message: function (response, failed_action) {
            response.json().then(function (jsonResponse) {
                if (jsonResponse.error.message) {
                    alert(jsonResponse.error.message)
                }
                else {
                    alert(`There was an error ${failed_action} the dataset release.`);
                    console.error({ params, jsonResponse });
                }
            });
        }
    };

});
