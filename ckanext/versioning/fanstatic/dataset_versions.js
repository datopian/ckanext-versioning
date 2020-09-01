/* API for ckanext-versioning */

"use strict";

ckan.module('dataset_version_controls', function ($) {

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
            this._tag = this.options.tag || null;

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

            this.$('.delete-version-btn').on('click', this._onDelete);
            this.$('.create-version-form').on('submit', this._onCreate);
            this.$('.update-version-form').on('submit', this._onUpdate);
            this.$('.revert-to-btn').on('click', this._onRevert);

            $(document).ready(this._onDocumentReady);
        },

        _onDocumentReady: function ()
        {
            this._loadTagList(this._packageId);
        },

        _onDelete: function (evt)
        {
            let dataset = $(evt.target).data('dataset');
            let tag = $(evt.target).data('version-id');
            tag = String(tag);

            if (confirm("Are you sure you want to delete the version \"" + tag + "\" of this dataset?")) {
                return this._delete(tag, dataset);
            }
        },

        _onCreate: function (evt)
        {
            let tagName = evt.target.querySelector("input[name=version_name]").value.trim();
            let description = evt.target.querySelector("textarea[name=details]").value.trim();
            evt.preventDefault();
            return this._create(this._packageId, tagName, description);
        },

        _onUpdate: function(evt)
        {
            let tagName = evt.target.querySelector("input[name=version_name]").value.trim();
            let description = evt.target.querySelector("textarea[name=details]").value.trim();

            evt.preventDefault();
            return this._update(this._packageId, this._tag, tagName, description);
        },

        _onRevert: function(evt)
        {
            let dataset = $(evt.target).data('dataset');
            let revision_ref = $(evt.target).data('version-id');
            revision_ref = String(revision_ref);

            if (confirm(
                "Are you sure you want to revert this dataset to the older tag \"" + revision_ref + "\"?\n\n" +
                "Note that when doing this the current state will be lost. If you want to preserve it, please cancel and create a tag for it first.")) {
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

        _loadTagList: function (datasetId) {
            let params = new URLSearchParams({"dataset": datasetId});
            let url = this._apiBaseUrl + 'dataset_tag_list?' + params;
            let that = this;

            fetch(url).then(function(response) {
                if (response.status !== 200) {
                    console.error("Failed to fetch list of tags, got HTTP " + response.status);
                } else {
                    response.json().then(function(payload) {
                        that._renderTagList(payload.result);
                    }).catch(function(e) {
                        console.error("Failed rendering list of tags: " + e);
                    });
                }
            }).catch(function(e) {
                console.error("Error fetching list of tags: " + e);
            });
        },

        _renderTagList: function (tags) {
            const loader = $('#tag-list .tags-list__loading');
            const table = $('#tag-list .tags-list__list');
            const noTagsMessage = $('#tag-list .tags-list__no-tags');
            const tagRowTemplate = $('tbody tr', table)[0];
            const tagHrefTemplate = $('.tags-list__tag-name a', tagRowTemplate).attr('href');

            loader.hide();

            if (tags.length < 1) {
                noTagsMessage.show();
                return;
            }

            $('tbody', table).empty();
            for (let i = 0; i < tags.length; i++) {
                let tag = tags[i];
                let row = $(tagRowTemplate).clone();
                table.append(row);
                $('.tags-list__tag-name a', row).attr('href', tagHrefTemplate.replace('__VERSION__', tag.name));
                $('.tags-list__tag-name a', row).text(tag.name);
                $('.tags-list__tag-description', row).text(tag.description);

                let datetime = $('<span class="automatic-local-datetime"/>');
                datetime.text(moment(tag.created).format('LL, LT ([UTC]Z)'));
                datetime.data('datetime', tag.created);
                $('.tags-list__tag-timestamp', row).append(datetime);
            }

            table.show();
        },

        _delete: function (tag, dataset) {
            const action = 'dataset_tag_delete';
            let params = {
                tag: tag,
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

        _create: function (datasetId, tagName, description) {
            const action = 'dataset_tag_create';
            let params = {
                dataset: datasetId,
                name: tagName,
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

        _update: function (datasetId, tag, tagName, description) {
            const action = 'dataset_tag_update';
            let params = {
                dataset: datasetId,
                tag: tag,
                name: tagName,
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
                        location.href = this._packageUrl;
                    }
                }.bind(this));
        },

        _show_error_message: function (response, failed_action) {
            response.json().then(function (jsonResponse) {
                if (jsonResponse.error.message) {
                    alert(jsonResponse.error.message)
                }
                else {
                    alert(`There was an error ${failed_action} the dataset tag.`);
                    console.error({ params, jsonResponse });
                }
            });
        }
    };

});
