"use strict";

/* releases-selector
 *
 * This JavaScript module generates an ajax call to get the list of releases
 * and adds option to a selector html element.
 *
 * includeCurrent - if the selector should include the "Current live revision" option
 * selectedId - selected tag name to display in the selector as selected value
 * datasetId - id of the dataset to get the releases list from
 *
 */
ckan.module('releases-selector', function ($) {
  return {
    initialize: function () {
        $.proxyAll(this, /_on/);
        $.proxyAll(this, /_render/);
        this._includeCurrent = this.options.includeCurrent;
        this._selectedId = this.options.selectedId;
        this._datasetId = this.options.datasetId;

        $(document).ready(this._onDocumentReady);
    },

    _onDocumentReady: function ()
    {
        this._loadReleaseList(this._datasetId);
    },

    _loadReleaseList: function(datasetId){
        this.sandbox.client.call(
            'GET',
            'dataset_release_list?',
            'dataset='+datasetId,
            this._renderReleaseSelector
            )
    },

    _renderReleaseSelector: function(json){
        let releases = json.result
        let element = "<option></option>"
        let that = this
        $.each(releases, function(i, release) {
            that.el
                .append(
                    $(element)
                        .attr("value", release.name)
                        .text(release.name)
                );
        });

        if(this._includeCurrent){
            this.el
                .append(
                    $(element)
                        .attr("value", "current")
                        .text(this._('[Current live revision]'))
                );
        }

        if (this._selectedId) {
            if(this._selectedId == 'current'){
                this.el.val("current")
            } else {
                this.el.val(this._selectedId)
            }
        }
    },

  };
});
