#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import re
import requests
import sys
import traceback
from datetime import datetime
from datetime import timedelta
from lxml import etree
import time
import shutil
from distutils.dir_util import copy_tree
import ConfigParser
import json


class Spider:

    def __init__(self, user_id, my_cookie, max_page, wait_time, start_date = "", end_date = ""):
        self.user = {}
        self.user_id = user_id  # 用户id，即需要我们输入的数字，如昵称为“Dear-迪丽热巴”的id为1669879400
        self.base_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep + "backup" + os.sep + str(self.user_id)
        self.filter = 0  # 取值范围为0、1，程序默认值为0，代表要爬取用户的全部微博，1代表只爬取用户的原创微博
        self.cookie = {"Cookie": my_cookie}
        self.max_page = max_page
        self.wait_time = wait_time
        self.start_date = start_date
        self.end_date = end_date

        self.weibos = []

    # 获取用户昵称
    def get_username(self):
        try:
            url = "https://weibo.cn/%d/info" % (self.user_id)
            html = requests.get(url, cookies=self.cookie).content
            selector = etree.HTML(html)
            username = selector.xpath("//title/text()")[0]
            self.user["username"] = username[:-3]
            print (u"username:" + self.user["username"]).encode("utf-8")
            return True
        except Exception, e:
            print "Error: ", e
            traceback.print_exc()
            return False

    # 获取用户微博数、关注数、粉丝数
    def get_user_info(self):
        try:
            url = "https://weibo.cn/u/%d?filter=%d&page=1" % (
                self.user_id, self.filter)
            html = requests.get(url, cookies=self.cookie).content
            selector = etree.HTML(html)
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
            self.user["following"] = int(guid[0])
            print "followings: " + str(self.user["following"])

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

    #def get_article(self, url, publish_time):
     #   html = requests.get(url, cookies=self.cookie).content
      #  selector = etree.HTML(html)

    def get_weibo_from_html(self, url, is_original_weibo, retweet_publish_time=""):
        pattern = r"\d+\.?\d*"

        new_weibo = {"publish_time":"", "author_name":"", "author_link":"", "weibo_content":"", "image_num":0, "up_num":0,
             "retweet_num":0, "comment_num":0, "resource_links":None, "original_weibo": None}

        html = requests.get(url, cookies=self.cookie).content
        selector = etree.HTML(html)
        main_node = selector.xpath("//div[@id='M_']")[0]
        author_anchor = main_node.xpath("div/a")[0]
        new_weibo["author_link"] = "https://weibo.cn" + author_anchor.attrib["href"]
        new_weibo["author_name"] = author_anchor.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")

        #publish time
        str_time = main_node.xpath("div/span[@class='ct']")
        str_time = str_time[0].xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
        new_weibo["publish_time"] = self.get_publish_time(str_time)

        #weibo content
        if is_original_weibo:
            weibo_elem = main_node.xpath("div/span[@class='ctt']")
            new_weibo["weibo_content"] = weibo_elem[0].xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
            #if new_weibo["weibo_content"].startswith(":"):
             #   new_weibo["weibo_content"] = new_weibo["weibo_content"][1:]
            #resources including articles
            resource_links = {}
            links = weibo_elem[0].xpath("a")
            for link in links:
                if 'href' in link.attrib and link.attrib['href'].startswith("http://weibo.cn/sinaurl"):
                    key = link.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")
                    resource_links[key] = link.attrib['href']
            new_weibo["resource_links"] = resource_links
        else:
            retweet_elem = main_node.xpath("div")[-1]
            new_weibo["weibo_content"] = retweet_elem.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8")

        #images
        if is_original_weibo:
            links = main_node.xpath("div/a/@href")
            image_links = []
            for link in links:
                if link.startswith("/mblog/picAll"):
                    image_links = []
                    image_html = requests.get("http://weibo.cn" + link, cookies=self.cookie).content
                    image_selector = etree.HTML(image_html)
                    sublinks = image_selector.xpath("//div/a/@href")
                    for sublink in sublinks:
                        if sublink.startswith("/mblog/oripic"):
                            image_links.append("http://weibo.cn" + sublink)
                    break
                elif link.startswith("/mblog/oripic"):
                    image_links.append("http://weibo.cn" + link)
            new_weibo["image_num"] = len(image_links)
            if len(image_links) > 0:
                if not retweet_publish_time:
                    self.download_images(image_links, new_weibo["publish_time"])
                else:
                    self.download_images(image_links, retweet_publish_time + "-retweet")


        # 点赞数 + 转发数
        str_infos = selector.xpath("//div/span/a")
        for str_info in str_infos:
            if str_info.attrib["href"].startswith("/attitude/"):
                str_zan = str_info.text
                guid = re.findall(pattern, str_zan, re.M)
                if len(guid) > 0:
                    new_weibo["up_num"] = int(guid[0])
            elif str_info.attrib["href"].startswith("/repost/"):
                str_retweeet = str_info.text
                guid = re.findall(pattern, str_retweeet, re.M)
                if len(guid) > 0:
                    new_weibo["retweet_num"] = int(guid[0])

        # 评论数
        comment_num_str = selector.xpath("//div/span[@class='pms']/text()")[0]
        guid = re.findall(pattern, comment_num_str, re.M)
        if len(guid) > 0:
            new_weibo["comment_num"] = int(guid[0])

        # get comments
        if new_weibo["comment_num"] > 0:
            comments = []

            if selector.xpath("//input[@name='mp']") == []:
                page_num = 1
            else:
                page_num = (int)(selector.xpath("//input[@name='mp']")[0].attrib["value"])
                comment_url = url.split('#')[0] + "&page="

            print "Downloading comments with %d pages" % (page_num)
            for page in range(1, page_num + 1):
                if page > 1:
                    html = requests.get(comment_url + str(page), cookies=self.cookie).content
                    selector = etree.HTML(html)
                comment_elems = selector.xpath("//div[@class='c']")
                for elem in comment_elems:
                    if 'id' in elem.attrib and elem.attrib['id'].startswith("C_"):
                        comments.append(elem.xpath("string(.)").encode("utf-8", "ignore").decode("utf-8"))
                if page % 5 == 0:
                    print "wait for %d seconds" % (self.wait_time)
                    time.sleep(self.wait_time)

            if not retweet_publish_time:
                self.write_comments(comments, new_weibo["publish_time"])
            else:
                self.write_comments(comments, retweet_publish_time + "-retweet")

        return new_weibo




    # 获取用户微博内容及对应的发布时间、点赞数、转发数、评论数
    def get_weibo_info(self):
        try:
            base_url = ""
            if self.start_date and self.end_date:
                base_url = "https://weibo.cn/%d/profile?hasori=0&haspic=0&starttime=%s&endtime=%s&advancedfilter=1" % (self.user_id, self.start_date, self.end_date)
            else:
                base_url = "https://weibo.cn/u/%d?filter=%d" % (self.user_id, self.filter)
            
            html = requests.get(base_url + "&page=1", cookies=self.cookie).content
            selector = etree.HTML(html)
            if selector.xpath("//input[@name='mp']") == []:
                page_num = 1
            else:
                page_num = (int)(selector.xpath("//input[@name='mp']")[0].attrib["value"])
            
            print "Total page num: " + str(page_num)
            if page_num > self.max_page:
                print "But you specified a max page num, it'll only download the first %d pages." % self.max_page
                page_num = self.max_page

            for page in range(1, page_num + 1):
                print "downloading page: %d" % (page)
                url2 = base_url + "&page=%d" % (page)
                html2 = requests.get(url2, cookies=self.cookie).content
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
                            self.weibos.append(forward_weibo)
                        elif len(comment_links) == 1:
                            #it's a original weibo
                            original_weibo = self.get_weibo_from_html(comment_links[0], True)
                            self.weibos.append(original_weibo)
                        else:
                            print "Error in finding comment links"
                        print "Sleep for 1 seconds before accessing next weibo. Please wait..."
                        time.sleep(1)

                print "Sleep for %d seconds before accessing next page. Please wait..." % (self.wait_time)
                time.sleep(self.wait_time)

        except Exception, e:
            print "Error: ", e
            traceback.print_exc()


    def write_weibo(self):
        try:
            name = "latest"
            file_path = self.base_dir + os.sep + "weibo" + os.sep + name + ".js"
            str = "Weibo['%s'] = " % (name) + json.dumps(self.weibos) + ";"
            f = open(file_path, "wb")
            f.write(str)
            f.close()
            print "Have successfully saved %d weibos" % (len(self.weibos))
        except Exception, e:
            print "Error: ", e
            traceback.print_exc()

    def mkdirs(self):
        weibo_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep + "backup"
        if not os.path.isdir(weibo_dir):
            os.mkdir(weibo_dir)
        base_dir = self.base_dir
        if not os.path.isdir(base_dir):
            os.mkdir(base_dir)
        img_dir = base_dir + os.sep + "images"
        if not os.path.isdir(img_dir):
            os.mkdir(img_dir)
        weibo_dir = base_dir + os.sep + "weibo"
        if not os.path.isdir(weibo_dir):
            os.mkdir(weibo_dir)
        comments_dir = base_dir + os.sep + "comments"
        if not os.path.isdir(comments_dir):
            os.mkdir(comments_dir)

    def write_comments(self, comments, name):
        file_path = self.base_dir + os.sep + "comments" + os.sep + name + ".js"
        str = "Comments['%s'] = " % (name) + json.dumps(comments) + ";"
        f = open(file_path, "wb")
        f.write(str)
        f.close()


    def write_user_info(self):
        file_path = self.base_dir + os.sep + "user.js"
        str = "var userInfo = " + json.dumps(self.user) + ";"
        f = open(file_path, "wb")
        f.write(str)
        f.close()

    def download_images(self, links, name):
        print "Downloading %d images for weibo %s" % (len(links), name)
        file_path_base = self.base_dir + os.sep + "images" + os.sep + name + "-"
        index = 1
        for img_url in links:
            file_path = file_path_base + "%d.jpg" % index
            try:
                img_url = re.sub(r"amp;", '', img_url)
                img_request = requests.get(img_url, cookies=self.cookie, stream=True)
                if img_request.status_code == 200:
                    with open(file_path, 'wb') as f:
                        img_request.raw.decode_content = True
                        shutil.copyfileobj(img_request.raw, f)
                else:
                    print "Bad response from server: %d" % img_request.status_code
                    print "Failed to download image #%d" %index
                    print "You can try to download manually later: " + img_url
            except:
                print "Failed to download image #%d" %index
                print "You can try to download manually later: " + img_url

            index += 1

    def moveFiles(self):
        print "Final step: copy some supporting files"
        src_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep
        dest_dir = self.base_dir + os.sep
        copy_tree(src_dir+"js", dest_dir+"js")
        copy_tree(src_dir+"css", dest_dir+"css")
        copy_tree(src_dir+"images", dest_dir+"images")
    
    # 运行爬虫
    def start(self):
        try:
            if self.get_username() == False:
                print "\nWeibo Backup Failed"
                print "==========================================================================="
                return
            self.get_user_info()
            self.mkdirs()
            self.write_user_info()
            self.get_weibo_info()
            self.write_weibo()
            self.moveFiles()
            print "\nCompleted successfully!"
            print "Please check the following directory to see results: " + self.base_dir
            print "==========================================================================="
        except Exception, e:
            print "Error: ", e


def main():
    try:
        config = ConfigParser.RawConfigParser()
        config.read('config.ini')
        user_id = config.getint('user_id', 'user_id')
        my_cookie = config.get('cookie', 'cookie')
        max_page = config.getint('max_page', 'max_page')
        wait_time = config.getint('wait_time', 'wait_time')
        start_date = config.get('date_range', 'start_date')
        end_date = config.get('date_range', 'end_date')
        print "Read config parameters: max_page=%d, wait_time=%d" % (max_page, wait_time)
        spider = Spider(user_id, my_cookie, max_page, wait_time)  # 调用Weibo类，创建微博实例wb
        spider.start()  # 爬取微博信息
    except Exception, e:
        print "Error: ", e
        traceback.print_exc()


if __name__ == "__main__":
    main()
