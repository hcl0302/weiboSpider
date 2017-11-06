var commentList;
var options = {
    valueNames: [ 'name', 'content', 'time' ],
    item: '<li><span class="name"></span><span class="content"></span><span class="time"></span></li>'
};

function getUrlVars() {
    var vars = [], hash;
    var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
    for(var i = 0; i < hashes.length; i++)
    {
        hash = hashes[i].split('=');
        vars.push(hash[0]);
        vars[hash[0]] = hash[1];
    }
    return vars;
}

$( document ).ready(function() {

    var params = getUrlVars();
    console.log(params);
    let id = params['id'];
    let year = params['year'];
    let month = params['month'];
    let retweet = params['retweet'];
    let title = params['title'];
    if (title == "retweet") {
        $("#title").html("微博转发");
    } else if (title == "comment") {
        $("#title").html("微博评论");
    } else {
        $("#title").html("微博点赞");
        options = {
            valueNames: [ 'name', 'time' ],
            item: '<li><span class="name"></span><span class="time"></span></li>'
        };
    }
    $.getJSON( "http://127.0.0.1:8081/interaction?id=" + id + "&year=" + year + "&month=" + month + "&retweet=" + retweet + "&title=" + title, function( data ) {
        console.log(data);
        var comments = [];
        if (title == "thumbup") {
            data.forEach(function(comment){
                comments.push({
                    name: comment.author_name,
                    time: comment.date
                });
            });
        } else {
            data.forEach(function(comment){
                comments.push({
                    name: comment.author_name,
                    content: comment.content,
                    time: comment.date
                });
            });
        }
        
        $('#loader').hide();
        commentList = new List('comments', options, comments);
    });
});