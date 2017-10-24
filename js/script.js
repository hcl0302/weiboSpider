var options = {
    valueNames: [ 'date', 'content', "upCount", "retweetCount", "commentCount" ]
};

var hackerList = new List('hacker-list', options);

$(document).ready(function() {
    $("#weiboCount").html(hackerList.size() + " original weibos in total");
    $("#matchCount").html(hackerList.size() + " original weibos matched in searching");
});

hackerList.on("searchComplete", function(){
    $("#matchCount").html(hackerList.matchingItems.length + " weibos matched in searching");
});