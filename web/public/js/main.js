
angular.module('weibo_summary', []).controller('controller', function($scope, $http) {

    $scope.init = function() {
        $scope.weiboPages = [];
        $scope.currentWeiboPage = null;
        $scope.pageSize = 10;

        $scope.pager = {
            pages: [],
            currentPage: 1, //This starts from 1
            totalPages: 0
        };
        
        $scope.searching = false;
        $scope.showOptions = false;
        $scope.options = {
            searchText: "",
            pageSize: 10,
            startDate: "",
            endDate: "",
            weiboType: "all",
            text: true,
            photo: true,
            article: true,
            others: true
        };
    }

    //check weibo advanced input
    //not all false

    $scope.init();

    $scope.doSearch = function() {
        $scope.searching = true;
        $scope.showOptions = false;
        var url = "http://127.0.0.1:8081/weibo";
        $scope.pageSize = $scope.options.pageSize;

        $http({
            method: 'POST',
            url: 'http://127.0.0.1:8081/weibo',
            data: $scope.options
        }).then(function successCallback(response){
            var data = angular.fromJson(response).data;

            var weibos = data.weibos;
            weibos.forEach(function(weibo){
                weibo.images = [];
                weibo.retweet_images = [];
                for (var i = 1; i <= weibo.image_num; i++) {
                    weibo.images.push("images/original/" + weibo.weibo_id + "-" + i + ".jpg");
                }
                for (var i = 1; i <= weibo.retweet_image_num; i++) {
                    weibo.retweet_images.push("images/retweet/" + weibo.retweet_weibo_id + "-" + i + ".jpg");
                }
            });
            $scope.currentWeiboPage = weibos;
            $scope.weiboPages[0] = weibos;

            //total pages
            let total = data.total;
            $scope.pager.totalPages = Math.ceil(total / $scope.pageSize);
            $scope.pager.pages = $scope.getPages($scope.pager.totalPages, 1, $scope.pageSize);
            $scope.pager.currentPage = 1;
            $scope.searching = false;
        }, function errorCallback(response){
            alert("The server returns an error: " + response);
        });
    }

    $scope.getPageData = function(page) {
        $scope.searching = true;
        var cachePage = $scope.getPageFromCache(page);
        if (cachePage) {
            $scope.currentWeiboPage = cachePage;
            $scope.searching = false;
            return;
        }
        var lastWeiboId = "", lastWeiboTime = "";
        cachePage = $scope.getPageFromCache(page-1);
        if (page > 0 && cachePage) {
            lastWeiboId = cachePage[$scope.pageSize-1].weibo_id;
            lastWeiboTime = cachePage[$scope.pageSize-1].publish_time;
        }

        $http({
            method: 'POST',
            url: 'http://127.0.0.1:8081/page',
            data: {
                page: page,
                lastWeiboId: lastWeiboId,
                lastWeiboTime: lastWeiboTime
            }
        }).then(function successCallback(response){
            var data = angular.fromJson(response).data;
            data.forEach(function(weibo){
                weibo.images = [];
                weibo.retweet_images = [];
                for (var i = 1; i <= weibo.image_num; i++) {
                    weibo.images.push("images/original/" + weibo.weibo_id + "-" + i + ".jpg");
                }
                for (var i = 1; i <= weibo.retweet_image_num; i++) {
                    weibo.retweet_images.push("images/retweet/" + weibo.retweet_weibo_id + "-" + i + ".jpg");
                }
            });
            $scope.currentWeiboPage = data;
            $scope.weiboPages[page-1] = data;
            $scope.searching = false;
        }, function errorCallback(response){
            alert("The server returns an error: " + response);
        });
    }

    $scope.getPageFromCache = function(page) {
        if ($scope.weiboPages.length >= page && $scope.weiboPages[page-1]) {
            return $scope.weiboPages[page-1];
        }
        return null;
    }

    $scope.toggleOptions = function() {
        $scope.showOptions = !$scope.showOptions;
    }

    $scope.setPage = function(page) {
        if (page < 1 || page > $scope.pager.totalPages) {
            return;
        }
        // get pager object from service
        $scope.pager.pages = $scope.getPages($scope.pager.totalPages, page, $scope.pageSize);
        $scope.pager.currentPage = page;

        $scope.getPageData(page);
    }

    $scope.getPages = function (totalPages, currentPage, pageSize) {
        // default to first page
        currentPage = currentPage || 1;
 
        var startPage, endPage;
        if (totalPages <= 10) {
            // less than 10 total pages so show all
            startPage = 1;
            endPage = totalPages;
        } else {
            // more than 10 total pages so calculate start and end pages
            if (currentPage <= 6) {
                startPage = 1;
                endPage = 10;
            } else if (currentPage + 4 >= totalPages) {
                startPage = totalPages - 9;
                endPage = totalPages;
            } else {
                startPage = currentPage - 5;
                endPage = currentPage + 4;
            }
        }
 
        // create an array of pages to ng-repeat in the pager control
        var pages = [];
        for (var i = startPage; i <= endPage; i++) {
            pages.push(i);
        }
        return pages;
    }

    $scope.getComments = function (weibo, retweet, title) {
        console.log(retweet);
        //let weibo = $scope.currentWeiboPage[index];
        var year, month, weibo_id;
        if (retweet) {
            year = weibo.retweet_publish_time.substring(0, 4);
            month = weibo.retweet_publish_time.substring(5, 7);
            weibo_id = weibo.retweet_weibo_id;
        } else {
            year = weibo.publish_time.substring(0, 4);
            month = weibo.publish_time.substring(5, 7);
            weibo_id = weibo.weibo_id;
        }
        retweet = retweet? 1:0;
        let url = "http://127.0.0.1:8081/comments.html?id=" + weibo_id + "&year=" + year + "&month=" + month + "&retweet=" + retweet + "&title=" + title;
        console.log(url);
        window.open(url, '_blank');
    }

    $scope.showRelationships = function() {
        window.open("http://127.0.0.1:8081/relationship.html", '_blank');
    }

    $scope.doSearch();

});