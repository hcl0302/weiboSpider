var author_list;
var options = {
    valueNames: [ 'name', 'weibo_num', 'up_num', 'retweet_num', 'comment_num' ],
    item: '<li><span class="name"></span><span class="weibo_num"></span><span class="up_num"></span><span class="retweet_num"></span><span class="comment_num"></span></li>'
};

$( document ).ready(function() {

    $.getJSON( "http://127.0.0.1:8081/relationships", function( data ) {
        console.log(data);
        var authors = [];
        data.forEach(function(author){
            authors.push({
                name: author.author_name,
                weibo_num: author.weibo_num,
                up_num: author.thumbup_num,
                retweet_num: author.forward_num,
                comment_num: author.comment_num
            });
        });
        $('#loader').hide();
        author_list = new List('author_list', options, authors);
    });
});