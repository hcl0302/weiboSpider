var express = require('express');
var bodyParser = require('body-parser');
var sqlite3 = require('sqlite3').verbose();

var db = new sqlite3.Database('./db/weibo.db', sqlite3.OPEN_READONLY, (err) => {
    if (err) {
        console.error(err.message);
    }
    console.log('Connected to the weibo database.');
});

var db_comment = null;
var db_comment_year = "";

var app = express();

var options;
var sql_base, sql_join, sql_where;

var getWeiboQuery = function() {
    sql_base = "SELECT * FROM weibo";
    sql_join = " left join retweet_weibo on weibo.original_weibo = retweet_weibo.retweet_weibo_id";
    sql_end = " ORDER BY weibo.publish_time DESC LIMIT " + options.pageSize;
    sql_where = " WHERE";
    if (options.weiboType == "original") {
        sql_where += " weibo.original_weibo is null AND";
    } else if (options.weiboType == "retweet") {
        sql_where += " weibo.original_weibo is not null AND";
    }

    if (options.endDate.length > 0) {
        sql_where += " weibo.publish_time<='" + options.endDate + "' AND";
    }
    if (options.startDate.length > 0) {
        sql_where += " weibo.publish_time>='" + options.startDate + "' AND";
    }

    if (!options.text) {
        sql_where += " weibo.weibo_type!=1 AND"
    }
    if (!options.photo) {
        sql_where += " weibo.weibo_type!=2 AND"
    }
    if (!options.others) {
        sql_where += " weibo.weibo_type!=4 AND"
    }
    if (!options.article) {
        sql_where += " weibo.weibo_type!=3 AND"
    }

    if (options.searchText.length > 0) {
        sql_where += " (weibo.weibo_content like '%" + options.searchText + "%' OR retweet_weibo.retweet_weibo_content like '%" + options.searchText + "%') AND";
    }

    if (sql_where.length == 6) {
        sql_where = "";
    } else {
        sql_where = sql_where.substring(0, sql_where.length-4);
    }

    return sql_base + sql_join + sql_where + sql_end;
}

var getCountQuery = function() {
    if (options.searchText.length > 0) {
        return "SELECT COUNT(*) FROM weibo" + sql_join + sql_where;
    }
    return "SELECT COUNT(*) FROM weibo" + sql_where;
}

var getPageQuery = function(page, lastWeiboId, lastWeiboTime) {
    let pageSize = options.pageSize;
    if (lastWeiboId != "" && lastWeiboTime != "") {
        var where = " WHERE weibo.publish_time<='" + lastWeiboTime + "' AND weibo.weibo_id!=" + lastWeiboId;
        if (sql_where.length > 0) {
            where = where + " AND " + sql_where.substring(6);
        }
        return sql_base + sql_join + where + sql_end;
    } else {
        return sql_base + sql_join + sql_where + sql_end + " OFFSET " + (pageSize*(page-1));
    }
}

// Create application/x-www-form-urlencoded parser
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());

app.use(express.static('public'));
app.get('/index.htm', function (req, res) {
    res.sendFile( __dirname + "/" + "index.htm" );
})

app.post('/weibo', function (req, res) {
    // Prepare output in JSON format
    options = req.body;
    console.log(options);
    let sql = getWeiboQuery();
    let count_sql = getCountQuery();

    console.log(sql);
    console.log(count_sql);
    response = {};

    db.serialize(function() {
        db.get(count_sql, [], (err, row) => {
            if (err) {
                throw err;
            }
            response.total = row["COUNT(*)"];
        });

        db.all(sql, [], (err, rows) => {
            if (err) {
                throw err;
            }
            result = true;
            response.weibos = rows;
            res.writeHead(200,{'Content-Type':'text/html;charset=utf-8'});
            res.end(JSON.stringify(response));
        });
    });
    
})

app.post('/page', function (req, res) {
    console.log(req.body);
    let lastWeiboId = req.body.lastWeiboId;
    let lastWeiboTime = req.body.lastWeiboTime;
    let page = req.body.page;

    let sql = getPageQuery(page, lastWeiboId, lastWeiboTime);
    console.log(sql);

    db.all(sql, [], (err, rows) => {
        if (err) {
            throw err;
        }
        res.writeHead(200,{'Content-Type':'text/html;charset=utf-8'});
        res.end(JSON.stringify(rows));
    });
})

app.get('/interaction', function(req, res) {
    let weibo_id = req.query.id;
    let year = req.query.year;
    let month = req.query.month;
    let retweet = req.query.retweet;
    let title = req.query.title;

    var tableName = title + "_" + month;
    if (retweet == 1) {
        tableName = "retweeted" + tableName;
    }

    let sql = "SELECT * FROM " + tableName + " WHERE weibo_id=" + weibo_id;
    console.log(sql);

    if (!(db_comment_year === year) && db_comment != null) {
        console.log(db_comment_year);
        db_comment.close();
        db_comment = null;
    }
    if (db_comment == null) {
        db_comment = new sqlite3.Database('./db/' + year + '.db', sqlite3.OPEN_READONLY, (err) => {
            if (err) {
                console.error(err.message);
            }
            console.log('Connected to the interaction database: ' + year);
            db_comment.all(sql, [], (err, rows) => {
                if (err) {
                    throw err;
                }
                res.end(JSON.stringify(rows));
            });
        });
        db_comment_year = year;
    } else {
        db_comment.all(sql, [], (err, rows) => {
            if (err) {
                throw err;
            }
            res.writeHead(200,{'Content-Type':'text/html;charset=utf-8'});
            res.end(JSON.stringify(rows));
        });
    }
    
})

app.get('/relationships', function(req, res) {

    let sql_authors = "SELECT * FROM author";

    db.all(sql_authors, [], (err, rows) => {
        if (err) {
            throw err;
        }
        res.writeHead(200,{'Content-Type':'text/html;charset=utf-8'});
        res.end(JSON.stringify(rows));
    });
    
})

var server = app.listen(8081, function () {
   console.log("Visit http://127.0.0.1:8081/");
   console.log("Press Ctrl-C to stop");
})
