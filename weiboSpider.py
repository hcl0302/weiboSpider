#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import re
import requests
import sys
import traceback
from datetime import datetime
from datetime import timedelta
from random import randint
from lxml import etree
import time
import shutil
from distutils.dir_util import copy_tree
import ConfigParser
import sqlite3


class Spider:

    def __init__(self, user_address, cookie, wait_time, mode, overwriting, download_options, start_date = "", end_date = ""):
        self.max_page = 99999999 #deprecated
        self.wait_time = wait_time
        self.start_date = start_date
        self.end_date = end_date
        self.overwriting = overwriting
        self.mode = mode

        self.download_weibo_comments_max = download_options[0]
        self.download_forwarded_weibo_comments_max = download_options[1]
        self.download_weibo_forwarding_max = download_options[2]
        self.download_forwarded_weibo_forwarding_max = download_options[3]
        self.download_weibo_thumbup_max = download_options[4]
        self.download_forwarded_weibo_thumbup_max = download_options[5]

        #self.cookies = cookies
        #print self.cookies
        #print self.proxies
        #self.cookie_index = 0
        self.request_counter = 0
        self.cookie = {"Cookie": cookie}
        #self.proxy = self.proxies[0]
        #self.headers = {'Connection': 'keep-alive',
        #   'User-Agent':'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Mobile Safari/537.36'}
        self.user = {"username": None}
        self.comment_db_year = None
        self.comment_db_month = None
        self.comment_conn = None
        self.db_conn = None
        self.db_cur = None


        if user_address.isdigit():
            self.user_id = int(user_address)
            self.user_address = None
        else:
            self.user_address = user_address
            self.user_id = self.get_user_id(user_address, False)
        if self.user_id:
            profile = self.get_user_profile(self.user_id)
            self.user["username"] = profile["username"]
            self.user["img"] = profile["img"]
        self.base_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep + "backup" + os.sep + str(self.user_id)
        self.filter = 0  # 取值范围为0、1，程序默认值为0，代表要爬取用户的全部微博，1代表只爬取用户的原创微博


    def change_cookie(self):
        self.request_counter += 1
        if self.request_counter <= 5:
            return
        #self.cookie_index += 1
        #if self.cookie_index >= len(self.cookies):
         #   self.cookie_index = 0
        #self.cookie = {"Cookie": self.cookies[self.cookie_index]}
        #self.proxy = self.proxies[self.cookie_index]
        self.request_counter = 0
        #print "Switch to use next account: " + str(self.cookie_index)
        wait_time = randint(5, self.wait_time)
        print "wait for %d seconds" % wait_time
        time.sleep(wait_time)
    
    def get_user_id(self, user_address, retweeted):
        try:
            url = "https://weibo.cn/" + user_address
            html = requests.get(url, cookies=self.cookie).content
            selector = etree.HTML(html)
            href = selector.xpath("//table/tr/td/a/@href")[0]
            index = href.find("/avatar")
            if index < 0:
                return None
            user_id = int(href[1:index])
            return user_id
        except Exception, e:
            print "Error: ", e
            traceback.print_exc()
            return None

    def get_user_profile(self, user_id):
        profile = {"username":None, "img":None}
        try:
            url = "https://weibo.cn/%d/info" % (user_id)
            html = requests.get(url,cookies=self.cookie).content
            selector = etree.HTML(html)
            username = selector.xpath("//title/text()")[0]
            profile["username"] = username[:-3]
            #download profile image_num
            image_link = selector.xpath("//div[@class='c']/img/@src")[0]
            profile["img"] = image_link
            return profile
        except Exception, e:
            print "Error: ", e
            traceback.print_exc()
            return None

    def write_user_info(self):
        try:
            self.db_cur.execute('''SELECT * FROM user''')
            if len(self.db_cur.fetchall()) == 0:
                self.db_cur.execute('''INSERT INTO user (user_id,user_name,followings,followers,weibo_num) 
                    VALUES(?,?,?,?,?)''', (self.user_id, self.user["username"], self.user["followings"], self.user["followers"], self.user["weibo_num"]))
                print "insert new user infomation into database"
            else:
                self.db_cur.execute('''UPDATE user SET user_name=?,followings=?,followers=?,weibo_num=?
                    WHERE user_id=?''', (self.user["username"], self.user["followings"], self.user["followers"], self.user["weibo_num"], self.user_id))
                print "update user infomation in database"
            self.db_conn.commit()
        except Exception, e:
            print "Error while writing user info into database: ", e


    # 获取用户微博数、关注数、粉丝数
    def get_user_info(self):
        try:
            self.base_url = ""
            if self.mode == 2:
                self.base_url = "https://weibo.cn/%d/profile?hasori=0&haspic=0&starttime=%s&endtime=%s&advancedfilter=1" % (self.user_id, self.start_date, self.end_date)
            else:
                self.base_url = "https://weibo.cn/u/%d?filter=%d" % (self.user_id, self.filter)
            
            html = requests.get(self.base_url + "&page=1", cookies=self.cookie).content
            selector = etree.HTML(html)
            if selector.xpath("//input[@name='mp']") == []:
                self.page_num = 1
            else:
                self.page_num = (int)(selector.xpath("//input[@name='mp']")[0].attrib["value"])

            pattern = r"\d+\.?\d*"

            # 微博数
            str_wb = selector.xpath(
                "//div[@class='tip2']/span[@class='tc']/text()")[0]
            guid = re.findall(pattern, str_wb, re.S | re.M)
            for value in guid:
                num_wb = int(value)
                break
            self.user["weibo_num"] = num_wb
            print "webo nums: " + str(self.user["weibo_num"])

            # 关注数
            str_gz = selector.xpath("//div[@class='tip2']/a/text()")[0]
            guid = re.findall(pattern, str_gz, re.M)
            self.user["followings"] = int(guid[0])
            print "followings: " + str(self.user["followings"])

            # 粉丝数
            str_fs = selector.xpath("//div[@class='tip2']/a/text()")[1]
            guid = re.findall(pattern, str_fs, re.M)
            self.user["followers"] = int(guid[0])
            print "followers: " + str(self.user["followers"])


        except Exception, e:
            print "Error: ", e
            traceback.print_exc()

    def get_publish_time(self, str_time):
        #publish_time = str_time.split(u'来自')[0]
        publish_time = str_time.strip()
        if u"刚刚" in publish_time:
            publish_time = datetime.now().strftime(
                '%Y-%m-%d %H:%M')
        elif u"分钟" in publish_time:
            minute = publish_time[:publish_time.find(u"分钟")]
            minute = timedelta(minutes=int(minute))
            publish_time = (
                datetime.now() - minute).strftime(
                "%Y-%m-%d %H:%M")
        elif u"今天" in publish_time:
            today = datetime.now().strftime("%Y-%m-%d")
            current_time = publish_time[3:]
            publish_time = today + " " + current_time
        elif u"月" in publish_time:
            year = datetime.now().strftime("%Y")
            month = publish_time[0:2]
            day = publish_time[3:5]
            hour = publish_time[7:12]
            publish_time = (
                year + "-" + month + "-" + day + " " + hour)
        else:
            publish_time = publish_time[:16]
        return publish_time

    def get_author_from_url(self, url):
        index = url.rfind('/') + 1
        return url[index:]

    def get_weibo_from_html(self, url, is_original_weibo, retweet_publish_time=""):
        pattern = r"\d+\.?\d*"

        new_weibo = {"publish_time":"", "author_name":"", "author_link":"", "weibo_content":"", "image_num":0, "up_num":0,"up_url":None,
             "retweet_num":0, "comment_num":0, "weibo_type":1, "resource_links":{}, "original_weibo": None}

        html = requests.get(url,cookies=self.cookie).content
        self.request_counter += 1
        selector = etree.HTML(html)
        main_node = selector.xpath("//div[@id='M_']")[0]
        author_anchor = main_node.xpath("div/a")[0]
        new_weibo["author_link"] = self.get_author_from_url(author_anchor.attrib["href"])
        new_weibo["author_name"] = author_anchor.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")

        #publish time
        str_time = main_node.xpath("div/span[@class='ct']")
        str_time = str_time[0].xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
        new_weibo["publish_time"] = self.get_publish_time(str_time)

        #weibo content
        if is_original_weibo:
            weibo_elem = main_node.xpath("div/span[@class='ctt']")
            new_weibo["weibo_content"] = weibo_elem[0].xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
            if new_weibo["weibo_content"].startswith(":"):
                new_weibo["weibo_content"] = new_weibo["weibo_content"][1:]
            #resources including articles
            resource_links = {}
            links = weibo_elem[0].xpath("a")
            for link in links:
                if 'href' in link.attrib and link.attrib['href'].startswith("http://weibo.cn/sinaurl"):
                    key = link.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
                    resource_links[key] = link.attrib['href']
                    new_weibo["weibo_type"] = 4
            new_weibo["resource_links"] = resource_links
        else:
            retweet_elem = main_node.xpath("div")[-1]
            new_weibo["weibo_content"] = retweet_elem.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
            new_weibo["weibo_content"] = new_weibo["weibo_content"].split(str_time)[0]
        new_weibo["weibo_content"] = new_weibo["weibo_content"].strip()

        #images
        if is_original_weibo:
            links = main_node.xpath("div/a/@href")
            image_links = []
            for link in links:
                if link.startswith("/mblog/picAll"):
                    image_links = []
                    image_html = requests.get("http://weibo.cn" + link,cookies=self.cookie).content
                    self.request_counter += 1
                    image_selector = etree.HTML(image_html)
                    sublinks = image_selector.xpath("//div/a/@href")
                    for sublink in sublinks:
                        if sublink.startswith("/mblog/oripic"):
                            image_links.append("http://weibo.cn" + sublink)
                    break
                elif link.startswith("/mblog/oripic"):
                    image_links.append("http://weibo.cn" + link)
            new_weibo["image_num"] = len(image_links)
            new_weibo["image_links"] = image_links
            if len(image_links) > 0:
                new_weibo["weibo_type"] = 2

        # 点赞数 + 转发数
        str_infos = selector.xpath("//div/span/a")
        for str_info in str_infos:
            if str_info.attrib["href"].startswith("/attitude/"):
                if new_weibo["up_url"] != None:
                    continue
                str_zan = str_info.text
                guid = re.findall(pattern, str_zan, re.M)
                if len(guid) > 0:
                    new_weibo["up_num"] = int(guid[0])
                    new_weibo["up_url"] = "https://weibo.cn" + str_info.attrib["href"]
            elif str_info.attrib["href"].startswith("/repost/"):
                str_retweeet = str_info.text
                guid = re.findall(pattern, str_retweeet, re.M)
                if len(guid) > 0:
                    new_weibo["retweet_num"] = int(guid[0])
                    new_weibo["retweet_url"] = "https://weibo.cn" + str_info.attrib["href"]

        # 评论数
        comment_num_str = selector.xpath("//div/span[@class='pms']/text()")[0]
        guid = re.findall(pattern, comment_num_str, re.M)
        if len(guid) > 0:
            new_weibo["comment_num"] = int(guid[0])

        #comments
        if new_weibo["comment_num"] > 0:
            new_weibo["comment_url"] = url.split('#')[0] + "&page="
            if selector.xpath("//input[@name='mp']") == []:
                new_weibo["comment_page_num"] = 1
            else:
                new_weibo["comment_page_num"] = (int)(selector.xpath("//input[@name='mp']")[0].attrib["value"])

        return new_weibo




    # 获取用户微博内容及对应的发布时间、点赞数、转发数、评论数
    def get_weibo_info(self):
        try:
            print "Total page num: " + str(self.page_num)
            if self.page_num > self.max_page:
                print "But you specified a max page num, it'll only download the first %d pages." % self.max_page
                self.page_num = self.max_page

            for page in range(1, self.page_num + 1):
                print "downloading page: %d" % (page)
                url2 = self.base_url + "&page=%d" % (page)
                html2 = requests.get(url2,cookies=self.cookie).content
                self.request_counter += 1
                selector2 = etree.HTML(html2)
                info = selector2.xpath("//div[@class='c']")
                if len(info) > 3:
                    for i in range(0, len(info) - 2):

                        #check whether it's original
                        comment_links = info[i].xpath("div/a[@class='cc']/@href")
                        if len(comment_links) > 1:
                            #it's a retweet weibo
                            forward_weibo = self.get_weibo_from_html(comment_links[1], False)
                            original_weibo = self.get_weibo_from_html(comment_links[0], True, forward_weibo["publish_time"])
                            forward_weibo["original_weibo"] = original_weibo
                            if self.write_weibo(forward_weibo) == None:
                                return
                        elif len(comment_links) == 1:
                            #it's a original weibo
                            original_weibo = self.get_weibo_from_html(comment_links[0], True)
                            if self.write_weibo(original_weibo) == None:
                                return
                        else:
                            print "Error in finding links to the weibo"
                        print "Sleep %d seconds before downloading next weibo, please wait..." % self.wait_time
                        time.sleep(self.wait_time)
                print "Sleep %d seconds before going to next page, please wait..." % self.wait_time
                time.sleep(self.wait_time)

        except Exception, e:
            print "Error: ", e
            traceback.print_exc()


    def write_weibo(self, weibo, retweeted = False):
        try:
            img_dir_name = "retweet" if retweeted else "original"
            if retweeted:
                self.db_cur.execute('''SELECT * FROM retweet_weibo WHERE (retweet_publish_time=?) AND (retweet_weibo_content=?)''', 
                    (weibo["publish_time"], weibo["weibo_content"]))
            else:
                self.db_cur.execute('''SELECT * FROM weibo WHERE (publish_time=?) AND (weibo_content=?)''', (weibo["publish_time"], weibo["weibo_content"]))
            row = self.db_cur.fetchone()
            original_weibo_id = None

            if row != None and self.mode == 1:
                print "Have downloaded all the latest weibos not in your local backup."
                return None

            if row != None and self.overwriting == False:
                weibo_id = row[0]
                print "Weibo(id: %d, retweeted: %s) already exists. Skip" % (weibo_id, retweeted)
                return weibo_id

            if weibo["original_weibo"] != None:
                original_weibo_id = self.write_weibo(weibo["original_weibo"], True)
                weibo["weibo_type"] = weibo["original_weibo"]["weibo_type"]

            if row == None:
                for key, value in weibo["resource_links"].iteritems():
                    article_url = self.get_article_url(value)
                    if article_url != None:
                        weibo["resource_links"][key] = article_url
                        weibo["weibo_type"] = 3
                        break


                if retweeted:
                    self.db_cur.execute('''INSERT INTO retweet_weibo (retweet_publish_time,retweet_author_address,retweet_author_name,retweet_image_num,retweet_weibo_content,
                        retweet_up_num,retweet_retweet_num,retweet_comment_num,retweet_weibo_type) 
                        VALUES(?,?,?,?,?,?,?,?,?)''', (weibo["publish_time"], weibo["author_link"],weibo["author_name"], weibo["image_num"], weibo["weibo_content"],
                        weibo["up_num"], weibo["retweet_num"], weibo["comment_num"], weibo["weibo_type"]))
                else:
                    self.db_cur.execute('''INSERT INTO weibo (publish_time,author_address,author_name,image_num,weibo_content,up_num,retweet_num,comment_num,weibo_type ,original_weibo) 
                        VALUES(?,?,?,?,?,?,?,?,?,?)''', (weibo["publish_time"], weibo["author_link"],weibo["author_name"], weibo["image_num"], weibo["weibo_content"],
                        weibo["up_num"], weibo["retweet_num"], weibo["comment_num"], weibo["weibo_type"], original_weibo_id))
                
                weibo_id = self.db_cur.lastrowid
                for key, value in weibo["resource_links"].iteritems():
                    self.add_resource(value, key, weibo_id, retweeted)
                self.update_author(weibo["author_link"], weibo["author_name"], 1, 0,0,0, False)
                print "inserted a new weibo(id: %d, retweeted: %s, publish_time: %s)" % (weibo_id, retweeted, weibo["publish_time"])
                if weibo["image_num"] > 0:
                    self.download_images(weibo["image_links"], str(weibo_id), img_dir_name)
                if weibo["comment_num"] > 0:
                    self.write_comments(weibo, weibo_id, retweeted)
                if weibo["up_num"] > 0:
                    self.write_thumbups(weibo, weibo_id, retweeted)
                if weibo["retweet_num"] > 0:
                    self.write_retweets(weibo, weibo_id, retweeted)
            
            elif self.overwriting == True:
                #update weibo, only update comments, re-download images, and update statistics nums
                #don't update author info, don't add new resources
                weibo_id = row[0]
                print "Weibo(id: %d, retweeted: %s) already exists. Overwriting" % (weibo_id, retweeted)
                if retweeted:
                    self.db_cur.execute('''UPDATE retweet_weibo SET retweet_up_num=?,retweet_retweet_num=?,retweet_comment_num=? 
                        WHERE retweet_weibo_id=?''',(weibo["up_num"],weibo["retweet_num"],weibo["comment_num"], weibo_id))
                else:
                    self.db_cur.execute('''UPDATE weibo SET up_num=?,retweet_num=?,comment_num=? WHERE weibo_id=?''',
                        (weibo["up_num"],weibo["retweet_num"],weibo["comment_num"], weibo_id))
                if weibo["image_num"] > 0:
                    self.download_images(weibo["image_links"], str(weibo_id), img_dir_name)
                if weibo["comment_num"] > 0:
                    self.write_comments(weibo, weibo_id, retweeted)
                if weibo["up_num"] > 0:
                    self.write_thumbups(weibo, weibo_id, retweeted)
                if weibo["retweet_num"] > 0:
                    self.write_retweets(weibo, weibo_id, retweeted)
                print "overwriting Weibo(id: %d, retweeted: %s) in database" % (weibo_id, retweeted)
            self.db_conn.commit()
            return weibo_id
        except Exception, e:
            print "Error while writing weibo into database: ", e
            traceback.print_exc()

    '''
    def get_userid_from_db(self, address, retweeted):
        if self.db_cur == None:
            return None
        try:
            table_name = "retweet_author" if retweeted else "author"
            user_id = None
            self.db_cur.execute("SELECT author_id FROM " + table_name + " WHERE author_address=?", (address,))
            row = self.db_cur.fetchone()
            if row:
                user_id = row[0]
            return user_id
        except Exception, e:
            print "Error while updating author info in database: ", e
            traceback.print_exc()
            return None
    '''

    def update_author(self, link, name, add_weibo, add_comment, add_forward, add_thumbup, retweeted):
        try:
            table_name = "retweet_author" if retweeted else "author"
            self.db_cur.execute("SELECT * FROM " + table_name +  " WHERE author_address=?", (link,))
            row = self.db_cur.fetchone()
            if row == None:
                if retweeted == False:
                    self.db_cur.execute("INSERT INTO " + table_name + ''' (author_address,author_name,weibo_num,comment_num,forward_num, thumbup_num)
                        VALUES(?,?,?,?,?,?)''', (link,name,add_weibo,add_comment,add_forward,add_thumbup))
                #else:
                    #self.db_cur.execute("INSERT INTO " + table_name + ''' (author_address,author_name,comment_num,forward_num, thumbup_num)
                        #VALUES(?,?,?,?,?)''', (link,name,add_comment,add_forward,add_thumbup))
                #print "insert new author(id: %d) infomation into database" % user_id
            #elif retweeted == True:
                #self.db_cur.execute("UPDATE " + table_name + ''' SET author_name=?,comment_num=?,forward_num=?,thumbup_num=?
                    #WHERE author_address=?''', (name, row[2]+add_comment, row[3]+add_forward, row[4]+add_thumbup, link))
            else:
                self.db_cur.execute("UPDATE " + table_name + ''' SET author_name=?,weibo_num=?,comment_num=?,forward_num=?,thumbup_num=?
                    WHERE author_address=?''', (name, row[2]+add_weibo, row[3]+add_comment, row[4]+add_forward, row[5]+add_thumbup, link))
        except Exception, e:
            print "Error while updating author info in database: ", e
            traceback.print_exc()

    def get_article_url(self, url):
        try:
            if url.startswith("http://"):
                url = "https" + url[4:]
            headers = requests.get(url, allow_redirects=False).headers
            if ("Location" in headers) and headers["Location"].find("/ttarticle") >= 0:
                url = headers["Location"]
                return url
            else:
                return None
        except Exception, e:
            print "Error while get article url: ", e
            traceback.print_exc()
            return None

    def add_resource(self, url, title, weibo_id, retweeted):
        try:
            if retweeted:
                self.db_cur.execute("INSERT INTO retweet_resource (url,title,retweet_weibo_id) VALUES(?,?,?)", (url, title, weibo_id))
            else:
                self.db_cur.execute("INSERT INTO resource (url,title,weibo_id) VALUES(?,?,?)", (url, title, weibo_id))
            print "insert new resource for weibo(id: %d) into database" % weibo_id
        except Exception, e:
            print "Error while adding resource into database: ", e
            traceback.print_exc()


    def download_images(self, links, name, dir_name):
        print "Downloading %d images for weibo %s" % (len(links), name)
        file_path_base = self.base_dir + os.sep + "public" + os.sep + "images" + os.sep + dir_name + os.sep + name + "-"
        index = 1
        for img_url in links:
            file_path = file_path_base + "%d.jpg" % index
            try:
                if os.path.isfile(file_path):
                    print "Image file(%s) already exists, Skip" % (file_path)
                    index += 1
                    continue
                img_url = re.sub(r"amp;", '', img_url)
                self.change_cookie()
                img_request = requests.get(img_url,cookies=self.cookie, stream=True)
                if img_request.status_code == 200:
                    with open(file_path, 'wb') as f:
                        img_request.raw.decode_content = True
                        shutil.copyfileobj(img_request.raw, f)
                else:
                    print "Failed to download image #%d" % index
            except:
                print "Failed to download image #%d" %index

            index += 1

    def init_db(self):
        db_file = self.base_dir + os.sep + "db" + os.sep + "weibo.db"
        try:
            self.db_conn = sqlite3.connect(db_file)
            self.db_cur = self.db_conn.cursor()
            self.db_cur.execute('''SELECT * FROM sqlite_master WHERE name ='user' and type='table';''')
            if len(self.db_cur.fetchall()) == 0:
                print "create tables in local database"
                self.db_cur.execute('''CREATE TABLE user (user_id INTEGER PRIMARY KEY NOT NULL, user_name TEXT NOT NULL, 
                    followings INTEGER NOT NULL, followers INTEGER NOT NULL, weibo_num INTEGER NOT NULL);''')
                self.db_cur.execute('''CREATE TABLE author (author_address TEXT PRIMARY KEY NOT NULL, author_name TEXT NOT NULL,
                    weibo_num INTEGER NOT NULL, comment_num INTEGER NOT NULL, forward_num INTEGER NOT NULL, thumbup_num INTEGER NOT NULL);''')
                self.db_cur.execute('''CREATE TABLE weibo (weibo_id INTEGER PRIMARY KEY, publish_time TEXT NOT NULL, author_address INTEGER NOT NULL, 
                    author_name TEXT NOT NULL, image_num INTEGER NOT NULL, weibo_content TEXT NOT NULL, up_num INTEGER NOT NULL, retweet_num INTEGER NOT NULL, 
                    comment_num INTEGER NOT NULL, weibo_type INTEGER NOT NULL, original_weibo INTEGER);''')
                self.db_cur.execute('''CREATE TABLE resource (resource_id INTEGER PRIMARY KEY, url TEXT NOT NULL, title TEXT NOT NULL,
                    weibo_id INTEGER NOT NULL, FOREIGN KEY(weibo_id) REFERENCES weibo(weibo_id));''')


                self.db_cur.execute('''CREATE TABLE retweet_weibo (retweet_weibo_id INTEGER PRIMARY KEY, retweet_publish_time TEXT NOT NULL, retweet_author_address INTEGER NOT NULL, 
                    retweet_author_name TEXT NOT NULL, retweet_image_num INTEGER NOT NULL, retweet_weibo_content TEXT NOT NULL, retweet_up_num INTEGER NOT NULL, retweet_retweet_num INTEGER NOT NULL, 
                    retweet_comment_num INTEGER NOT NULL, retweet_weibo_type INTEGER NOT NULL);''')
                #self.db_cur.execute('''CREATE TABLE retweet_author (author_address TEXT PRIMARY KEY NOT NULL, author_name TEXT NOT NULL,
                    #comment_num INTEGER NOT NULL,forward_num INTEGER NOT NULL, thumbup_num INTEGER NOT NULL);''')
                self.db_cur.execute('''CREATE TABLE retweet_resource (resource_id INTEGER PRIMARY KEY, url TEXT NOT NULL, title TEXT NOT NULL,
                    retweet_weibo_id INTEGER NOT NULL, FOREIGN KEY(retweet_weibo_id) REFERENCES retweet_weibo(retweet_weibo_id));''')
                self.db_conn.commit()
        except Exception, e:
            print "Error while init database: ", e
    
    def clean_up(self):
        if self.comment_conn != None:
            self.comment_conn.close()
        if self.db_conn != None:
            self.db_conn.close()


    def mkdirs(self):
        weibo_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep + "backup"
        if not os.path.isdir(weibo_dir):
            os.mkdir(weibo_dir)
        base_dir = self.base_dir
        if not os.path.isdir(base_dir):
            os.mkdir(base_dir)
            self.move_files()
        img_dir = base_dir + os.sep + "public" + os.sep + "images"
        if not os.path.isdir(img_dir):
            os.mkdir(img_dir)
        img_original_dir = img_dir + os.sep + "original"
        if not os.path.isdir(img_original_dir):
            os.mkdir(img_original_dir)
        img_retweet_dir = img_dir + os.sep + "retweet"
        if not os.path.isdir(img_retweet_dir):
            os.mkdir(img_retweet_dir)
        img_author_dir = img_dir + os.sep + "author"
        if not os.path.isdir(img_author_dir):
            os.mkdir(img_author_dir)
        db_dir = base_dir + os.sep + "db"
        if not os.path.isdir(db_dir):
            os.mkdir(db_dir)

    def move_files(self):
        print "Copy some supporting files"
        src_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep + "web"
        copy_tree(src_dir, self.base_dir)

    def init_interaction_db(self, year, month):
        try:
            db_file = self.base_dir + os.sep + "db" + os.sep + "%s.db" % year
            self.comment_db_year = year
            self.comment_db_month = month
            self.comment_conn = sqlite3.connect(db_file)
            self.comment_cur = self.comment_conn.cursor()
            self.create_interaction_tables(month)
        except Exception, e:
            print "Error while init interaction databases: ", e

    def create_interaction_tables(self, month):
        try:
            comment_table = "comment_" + month
            retweeted_comment_table = "retweeted" + comment_table
            retweet_table = "retweet_" + month
            retweeted_retweet_table = "retweeted" + retweet_table
            thumbup_table = "thumbup_" + month
            retweeted_thumbup_table = "retweeted" + thumbup_table
            self.comment_cur.execute("CREATE TABLE IF NOT EXISTS " + comment_table + ''' (id INTEGER PRIMARY KEY, author_link TEXT NOT NULL, 
                author_name TEXT NOT NULL, content TEXT NOT NULL, date TEXT NOT NULL, weibo_id INTEGER NOT NULL);''')
            self.comment_cur.execute("CREATE TABLE IF NOT EXISTS " + retweeted_comment_table + ''' (id INTEGER PRIMARY KEY, author_link TEXT NOT NULL, 
                author_name TEXT NOT NULL, content TEXT NOT NULL, date TEXT NOT NULL, weibo_id INTEGER NOT NULL);''')
            self.comment_cur.execute("CREATE TABLE IF NOT EXISTS " + retweet_table + ''' (id INTEGER PRIMARY KEY, author_link TEXT NOT NULL, 
                author_name TEXT NOT NULL, content TEXT NOT NULL, date TEXT NOT NULL, weibo_id INTEGER NOT NULL);''')
            self.comment_cur.execute("CREATE TABLE IF NOT EXISTS " + retweeted_retweet_table + ''' (id INTEGER PRIMARY KEY, author_link TEXT NOT NULL, 
                author_name TEXT NOT NULL, content TEXT NOT NULL, date TEXT NOT NULL, weibo_id INTEGER NOT NULL);''')
            self.comment_cur.execute("CREATE TABLE IF NOT EXISTS " + thumbup_table + ''' (id INTEGER PRIMARY KEY, author_link TEXT NOT NULL, 
                author_name TEXT NOT NULL, date TEXT NOT NULL, weibo_id INTEGER NOT NULL);''')
            self.comment_cur.execute("CREATE TABLE IF NOT EXISTS " + retweeted_thumbup_table + ''' (id INTEGER PRIMARY KEY, author_link TEXT NOT NULL, 
                author_name TEXT NOT NULL, date TEXT NOT NULL, weibo_id INTEGER NOT NULL);''')
            self.comment_conn.commit()
        except Exception, e:
            print "Error while creating interaction tables: ", e

    def find_latest_saved_interaction(self, weibo_id, weibo_date, table_prefix, retweeted):
        table_name = table_prefix + weibo_date[5:7]
        if retweeted:
            table_name = "retweeted" + table_name
        try:
            if self.comment_db_year == None:
                self.init_interaction_db(weibo_date[0:4], weibo_date[5:7])
            elif self.comment_db_year != weibo_date[0:4]:
                self.comment_cur.close()
                self.comment_conn.close()
                self.init_interaction_db(weibo_date[0:4], weibo_date[5:7])
            elif self.comment_db_month != weibo_date[5:7]:
                self.comment_db_month = weibo_date[5:7]
                self.create_interaction_tables(self.comment_db_month)
            self.comment_cur.execute("SELECT date from " + table_name + " WHERE weibo_id=? ORDER BY date DESC LIMIT 1", (weibo_id,))
            row = self.comment_cur.fetchone()
            if row == None:
                return None
            else:
                return row[0]
        except Exception, e:
            print "Error while finding latest comment from database: ", e

    def get_comments(self, weibo, weibo_id, retweeted):
        page_num = weibo["comment_page_num"]
        comment_url = weibo["comment_url"]
        comments = []
        last_date = self.find_latest_saved_interaction(weibo_id, weibo["publish_time"], "comment_", retweeted)
        print "Downloading comments with %d pages" % (page_num)
        for page in range(1, page_num + 1):
            self.change_cookie()
            html = requests.get(comment_url + str(page),cookies=self.cookie).content
            selector = etree.HTML(html)
            comment_elems = selector.xpath("//div[@class='c']")
            for elem in comment_elems:
                if 'id' in elem.attrib and elem.attrib['id'].startswith("C_"):
                    comment = {"content":"", "author_link":"", "author_name":"", "reply_to_link":None, "reply_to_name":None, "date":""}
                    author = elem.xpath("a")[0]
                    comment["author_name"] = author.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
                    comment["author_link"] = self.get_author_from_url(author.attrib["href"])
                    content = elem.xpath("span[@class='ctt']")[0]
                    comment["content"] = content.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
                    reply_to = content.xpath("a")
                    if len(reply_to) > 0:
                        comment["reply_to_name"] = reply_to[0].text
                        comment["reply_to_link"] = reply_to[0].attrib["href"]
                    str_time = elem.xpath("span[@class='ct']")[0].xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
                    str_time = str_time.split(u'来自')[0]
                    comment["date"] = self.get_publish_time(str_time)
                    if last_date != None and last_date >= comment["date"]:
                        print "Found old comments already exist. Skip"
                        return comments
                    comments.append(comment)
            if (comments and self.download_forwarded_weibo_comments_max <= len(comments)) or (not retweeted and self.download_weibo_comments_max <= len(comments)):
                print "comments of this weibo has reached max number, skip the rests"
                return comments
        return comments

    def write_comments(self, weibo, weibo_id, retweeted):
        if (retweeted and self.download_forwarded_weibo_comments_max == 0) or (not retweeted and self.download_weibo_comments_max == 0):
            return
        
        weibo_date = weibo["publish_time"]
        comments = self.get_comments(weibo, weibo_id, retweeted)
        if len(comments) == 0:
            return
        table_name = "comment_" + weibo_date[5:7]
        if retweeted:
            table_name = "retweeted" + table_name
        try:
            records = []
            for comment in comments:
                record = (comment["author_link"], comment["author_name"], comment["content"], comment["date"], weibo_id)
                if retweeted == False:
                    self.update_author(comment["author_link"], comment["author_name"], 0, 1,0,0, retweeted)
                records.append(record)
            
            self.comment_cur.executemany("INSERT INTO " + table_name + " (author_link,author_name,content,date,weibo_id) VALUES(?,?,?,?,?)", records)
            
            self.comment_conn.commit()
        except Exception, e:
            print "Error while writing comments into database: ", e

    def get_retweets(self, weibo, weibo_id, retweeted):
        retweet_url = weibo["retweet_url"]
        retweets = []
        last_date = self.find_latest_saved_interaction(weibo_id, weibo["publish_time"], "retweet_", retweeted)

        #get retweets page num
        self.change_cookie()
        html = requests.get(retweet_url,cookies=self.cookie).content
        selector = etree.HTML(html)
        if selector.xpath("//input[@name='mp']") == []:
            page_num = 1
        else:
            page_num = (int)(selector.xpath("//input[@name='mp']")[0].attrib["value"])
        retweet_url = retweet_url.split('#')[0] + "&page="

        print "Downloading forwardings with %d pages" % (page_num)
        for page in range(1, page_num + 1):
            if page > 1:
                self.change_cookie()
                html = requests.get(retweet_url + str(page),cookies=self.cookie).content
                selector = etree.HTML(html)
            retweet_elems = selector.xpath("//div[@class='c']")
            for elem in retweet_elems:
                zan = elem.xpath("span[@class='cc']")
                if len(zan) > 0:
                    retweet = {"content":"", "author_link":"", "author_name":"", "date":""}
                    author = elem.xpath("a")[0]
                    retweet["author_name"] = author.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
                    retweet["author_link"] = self.get_author_from_url(author.attrib["href"])
                    retweet["content"] = elem.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
                    zan_str = zan[0].xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
                    retweet["content"] = retweet["content"].split(zan_str)[0]
                    retweet["content"].replace(retweet["author_name"], "", 1)

                    str_time = elem.xpath("span[@class='ct']")[0].xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
                    str_time = str_time.split(u'来自')[0]
                    retweet["date"] = self.get_publish_time(str_time)
                    if last_date != None and last_date >= retweet["date"]:
                        print "Found old forwardings already exist. Skip"
                        return retweets
                    retweets.append(retweet)
            if (retweeted and self.download_forwarded_weibo_forwarding_max <= len(retweets)) or (not retweeted and self.download_weibo_forwarding_max <= len(retweets)):
                print "forwardings of this weibo has reached max number, skip the rests"
                return retweets
        return retweets

    def write_retweets(self, weibo, weibo_id, retweeted):
        if (retweeted and self.download_forwarded_weibo_forwarding_max == 0) or (not retweeted and not self.download_weibo_forwarding_max == 0):
            return
        
        weibo_date = weibo["publish_time"]
        retweets = self.get_retweets(weibo, weibo_id, retweeted)
        if len(retweets) == 0:
            return
        table_name = "retweet_" + weibo_date[5:7]
        if retweeted:
            table_name = "retweeted" + table_name
        try:
            records = []
            for retweet in retweets:
                record = (retweet["author_link"], retweet["author_name"], retweet["content"], retweet["date"], weibo_id)
                if retweeted == False:
                    self.update_author(retweet["author_link"], retweet["author_name"], 0,0, 1,0, retweeted)
                records.append(record)
            
            self.comment_cur.executemany("INSERT INTO " + table_name + " (author_link,author_name,content,date,weibo_id) VALUES(?,?,?,?,?)", records)
            
            self.comment_conn.commit()
        except Exception, e:
            print "Error while writing forwardings into database: ", e

    def get_thumbups(self, weibo, weibo_id, retweeted):
        thumbup_url = weibo["up_url"]
        thumbups = []
        last_date = self.find_latest_saved_interaction(weibo_id, weibo["publish_time"], "thumbup_", retweeted)

        #get thumbups page num
        self.change_cookie()
        html = requests.get(thumbup_url,cookies=self.cookie).content
        selector = etree.HTML(html)
        if selector.xpath("//input[@name='mp']") == []:
            page_num = 1
        else:
            page_num = (int)(selector.xpath("//input[@name='mp']")[0].attrib["value"])
        thumbup_url = thumbup_url.split('#')[0] + "&page="

        print "Downloading thumbups with %d pages" % (page_num)
        for page in range(1, page_num + 1):
            if page > 1:
                self.change_cookie()
                html = requests.get(thumbup_url + str(page),cookies=self.cookie).content
                selector = etree.HTML(html)
            thumbup_elems = selector.xpath("//div[@class='c' and not(@id)]")
            for elem in thumbup_elems:
                span_time = elem.xpath("span[@class='ct']")
                if len(span_time) > 0:
                    thumbup = {"author_link":"", "author_name":"", "date":""}
                    author = elem.xpath("a")[0]
                    thumbup["author_name"] = author.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
                    thumbup["author_link"] = self.get_author_from_url(author.attrib["href"])

                    str_time = span_time[0].xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
                    thumbup["date"] = self.get_publish_time(str_time)
                    if last_date != None and last_date >= thumbup["date"]:
                        print "Found old thumbups already exist. Skip"
                        return thumbups
                    thumbups.append(thumbup)
            if (retweeted and self.download_forwarded_weibo_thumbup_max <= len(thumbups)) or (not retweeted and self.download_weibo_thumbup_max <= len(thumbups)):
                print "thumbups of this weibo has reached max number, skip the rests"
                return thumbups

        return thumbups

    def write_thumbups(self, weibo, weibo_id, retweeted):
        if (retweeted and self.download_forwarded_weibo_thumbup_max == 0) or (not retweeted and self.download_weibo_thumbup_max == 0):
            return
        
        weibo_date = weibo["publish_time"]
        thumbups = self.get_thumbups(weibo, weibo_id, retweeted)
        if len(thumbups) == 0:
            return
        table_name = "thumbup_" + weibo_date[5:7]
        if retweeted:
            table_name = "retweeted" + table_name
        try:
            records = []
            for thumbup in thumbups:
                record = (thumbup["author_link"], thumbup["author_name"], thumbup["date"], weibo_id)
                if retweeted == False:
                    self.update_author(thumbup["author_link"], thumbup["author_name"], 0,0, 0,1, retweeted)
                records.append(record)
            
            self.comment_cur.executemany("INSERT INTO " + table_name + " (author_link,author_name,date,weibo_id) VALUES(?,?,?,?)", records)
            
            self.comment_conn.commit()
        except Exception, e:
            print "Error while writing thumbups into database: ", e

    # 运行爬虫
    def start(self):
        try:
            if self.user_id == None or self.user["username"] == None:
                print "\nWeibo Backup Failed"
                print "==========================================================================="
                return
            self.get_user_info()
            self.mkdirs()
            self.init_db()
            if self.db_cur == None or self.db_conn == None:
                print "\nWeibo Backup Failed"
                print "==========================================================================="
                return
            self.write_user_info()
            self.get_weibo_info()
            self.clean_up()
            print "\nCompleted successfully!"
            print "Please check the following directory to see results: " + self.base_dir
            print "==========================================================================="
        except Exception, e:
            print "Error: ", e
            traceback.print_exc()

def main():
    try:
        config = ConfigParser.RawConfigParser()
        config.read('config.ini')

        cookie = config.get('cookie', 'cookie')
        user_address = config.get('user', 'user')
        wait_time = config.getint('wait_time', 'wait_time')
        start_date = config.get('mode', 'start_date')
        end_date = config.get('mode', 'end_date')
        mode = config.getint('mode', 'mode')
        overwriting = config.getint('mode', 'overwriting')
        overwriting = False if overwriting==0 else True

        download_weibo_comments_max = config.getint('comments', 'download_weibo_comments_max')
        download_forwarded_weibo_comments_max = config.getint('comments', 'download_forwarded_weibo_comments_max')
        download_weibo_forwarding_max = config.getint('forwarding', 'download_weibo_forwarding_max')
        download_forwarded_weibo_forwarding_max = config.getint('forwarding', 'download_forwarded_weibo_forwarding_max')
        download_weibo_thumbup_max = config.getint('thumbup', 'download_weibo_thumbup_max')
        download_forwarded_weibo_thumbup_max = config.getint('thumbup', 'download_forwarded_weibo_thumbup_max')
        download_options = [download_weibo_comments_max, download_forwarded_weibo_comments_max, download_weibo_forwarding_max,
                            download_forwarded_weibo_forwarding_max,download_weibo_thumbup_max,download_forwarded_weibo_thumbup_max]

        if mode == 1:
            print "mode=%d: [Update Mode]" % mode
        elif mode == 2:
            print "mode=%d, start_date=%s, end_date=%s, overwriting=%d" % (mode,start_date,end_date,overwriting)
        else:
            print "Got an unrecognized mode: mode=%d" % mode
            return
        print "Press Ctrl+C to stop the program when an error happens or you want to quit"
        print "==========================================================================="
        spider = Spider(user_address, cookie, wait_time, mode, overwriting, download_options, start_date, end_date)
        spider.start()  # 爬取微博信息
    except Exception, e:
        print "Error: ", e
        traceback.print_exc()


if __name__ == "__main__":
    main()
