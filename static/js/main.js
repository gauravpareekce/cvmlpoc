/* global $, window */

$(function () {
    'use strict';
    $('#fileupload').fileupload({
        url: '/upload',        
        dataType: 'json',
        autoUpload: true,
        acceptFileTypes: /(\.|\/)(jpe?g)$/i,
        maxFileSize: 1000000, // 5 MB
        // Enable image resizing, except for Android and Opera,
        // which actually support image resizing, but fail to
        // send Blob objects via XHR requests:
        disableImageResize: /Android(?!.*Chrome)|Opera/
            .test(window.navigator.userAgent),
        imageMaxWidth: 512,
        imageMaxHeight: 512,
        imageCrop: true // Force cropped images
    }).on('fileuploadprogressall', function (e, data) {
        var progress = parseInt(data.loaded / data.total * 100, 10);
        $('#progress .progress-bar').css(
            'width',
            progress + '%'
        );
    }).on('fileuploaddone', function (e, data) {
        var divFile = $('<div/>').appendTo('#files');
        $.each(data.result.files, function (index, file) {
            var node = $('<p/>')
                    .append($('<span/>').text(file.name));           
            var link = $('<a>')
                .attr('target', '_blank')
                .prop('href', file.url);
                node.wrap(link);
            node.appendTo(divFile);
        });
    }).on('fileuploadfail', function (e, data) {
        data.context = $('<div/>').appendTo('#files');
        $.each(data.result.files, function (index, file) {
            var error = $('<span/>').text(file.error);
            $(data.context.children()[index])
                .append('<br>')
                .append(error);
        });
    })
});

function start_long_task() {
            // add task status elements
            div = $('<div class="progress"><div></div><div>0%</div><div>...</div><div>&nbsp;</div></div><hr>');
            $('#taskprogress').append(div);
            // create a progress bar
            var nanobar = new Nanobar({
                bg: '#44f',
                target: div[0].childNodes[0]
            });
            // send ajax POST request to start background job
            $.ajax({
                type: 'POST',
                url: '/longtask',
                success: function(data, status, request) {
                    status_url = request.getResponseHeader('Location');
                    update_progress(status_url, nanobar, div[0]);
                },
                error: function() {
                    alert('Unexpected error');
                }
            });
        }
        function update_progress(status_url, nanobar, status_div) {
            // send GET request to status URL
            $.getJSON(status_url, function(data) {
                // update UI
                percent = parseInt(data['current'] * 100 / data['total']);
                nanobar.go(percent);
                $(status_div.childNodes[1]).text(percent + '%');
                $(status_div.childNodes[2]).text(data['status']);
                if (data['state'] != 'PENDING' && data['state'] != 'PROGRESS') {
                    if ('result' in data) {
                        // show result
                        $(status_div.childNodes[3]).text('Result: ' + data['result']);
                    }
                    else {
                        // something unexpected happened
                        $(status_div.childNodes[3]).text('Result: ' + data['state']);
                    }
                }
                else {
                    // rerun in 2 seconds
                    setTimeout(function() {
                        update_progress(status_url, nanobar, status_div);
                    }, 2000);
                }
            });
    }

$(function() {
    $('#start-bg-job').click(start_long_task);
});