$(document).ready(function() {
    $('#search_section').hide();
    update_view();

    // form validation
    $('#file_input').change(function() {
        var file = this.files[0];
        var name = file.name;
        var size = file.size;
        var type = file.type;

        //Your validation
        allowed_filetypes = ["video/mov", "video/mpeg4", "video/mp4", "video/avi"];

        if (!allowed_filetypes.includes(type))
            $('#upload_err_msg').append("Upload must be a mov/mpeg4/mp4/avi video file.");
        else if (size > 500000000 || size < 0)
            $('#upload_err_msg').append(size);
        else
            video_id = randId()
        $('#video_id').val(video_id);
        submit_form(video_id);
    });

    // generate unique ID for each video upload
    function randId() {
        return Math.random().toString(36).substr(2, 10);
    }

    function submit_form(video_id) {
        var formData = new FormData($('#upload_form')[0]);
        $.ajax({
            url: '/upload_video',
            type: 'POST',
            data: formData,
            cache: false,
            contentType: false,
            processData: false,
            success: function(data) {
                data = JSON.parse(data);
                update_view();
                process_video(data.video_id);
            }
        });
    }

    // query the NoSQL Media server for all uploads, 
    // and update the view asynchronously
    function update_view() {
        // query the server for all uploads
        $.ajax({
            url: '/get_uploads',
            type: 'GET',
            success: function(data) {
                // repopulate the view

                data = JSON.parse(data);

                $('.upload_row').remove();
                for (var i = 0; i < data.uploads.length; i++) {
                    entity = data.uploads[i];

                    orig_filename = entity.orig_filename;
                    upload_time = new Date(Math.round(entity.upload_time) * 1000);
                    status = entity.status;
                    video_id = entity.video_id

                    $("#uploads_table_rows").append("<tr class='upload_row center' id='" + video_id + "'><td>" + orig_filename + "</td><td>" + upload_time + "</td><td>" + status + "</td></tr>");
                }
            }
        });
    }

    // process videos for audio/visual contents and index for retrieval
    function process_video(video_id) {
        $.ajax({
            url: '/process_video',
            type: 'GET',
            data: {
                'video_id': video_id
            },
            success: function(data) {
                //move items from processing section to library
                update_view();
            },
        });
    }

    // after user stops typing query, send  query to server
    $('#search_box').keyup(_.debounce(function() {
        var query = $('#search_box').val();

        if (query == "") {
            $('.search_row').remove();
            $('#uploads_section').show();
            $('#search_section').hide();
            $('#main_title').text("Uploads");
            update_view();

        } else {
            $('.search_row').remove();
            $('#uploads_section').hide();
            $('#search_section').show();
            $('#main_title').text("Searching");

            $.ajax({
                url: '/search',
                type: 'GET',
                data: {
                    'q': query
                },
                success: function(data) {
                    data = JSON.parse(data);
                    $('.search_row').remove();
                    for (var i = 0; i < data.length; i++) {
                        res = data[i];
                        $("#search_table_rows").append("<tr class='search_row center' id='" + res.video_id + "'><td>" +
                            res.video_id + "</td><td>" + res.content + "</td><td>" + Math.round(res.start_time) + "</td><td>" +
                            Math.round(res.end_time) + "</td><td>" + res.score + "</td></tr>");
                    }
                }
            });
        }
    }, 500));
});

// special event handler for class that doesn't belong to any DOM yet
$(document).on('click', '#search_table_rows tr.search_row', function(e) {
    // get the video_id and start_time
    video_id = this.id;
    start_time = $(this).find('td:eq(2)').html();

    // update the video
    src = '/uploads/' + video_id + '#t=' + start_time;
    $("#mp4_video").html("<source src='" + src + "' type='video/mp4'></source>");
});

// special event handler for class that doesn't belong to any DOM yet
$(document).on('click', '#uploads_table_rows tr.upload_row', function(e) {
    // get the video_id and start_time
    video_id = this.id;

    // update the video
    src = '/uploads/' + video_id;
    $("#uploads_mp4_video").html("<source src='" + src + "' type='video/mp4'></source>");
});