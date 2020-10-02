"use strict";

/* releases-selector
 *
 * This JavaScript module generates an ajax call to get the list of releases
 * and adds html as as options to a selector html element
 *
 * includeCurrent - if the selector should include the Current live version option
 * selectedId - selected revision_ref to display in the selector
 * packageId - id of the package to the the releases list
 *
 */
ckan.module('releases-selector', function ($) {
  return {
    initialize: function () {
        console.log('Initialize releases-selector.js')
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
            this._renderReleaseList
            )
    },

    _renderReleaseList: function(json){
        const releases = json.result
        let element = "<option></option>"
        let that = this

        $.each(releases, function(i, release) {
            that.el
                .append(
                    $(element)
                        .attr("value", release.revision_ref)
                        .attr("selected", this._selectedId == release.revision_ref ? 1 : "selected")
                        .text(release.name)
                );
        });

        if(this._includeCurrent){
            that.el
                .append(
                    $(element)
                        .attr("value", "current")
                        .text(this._('[Current live version]'))
                );
        }
    },

  };
});
