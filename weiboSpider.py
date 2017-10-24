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


class Weibo:

    # Weibo类初始化
    def __init__(self, user_id, my_cookie, max_page, wait_time, filter=0):
        self.user_id = user_id  # 用户id，即需要我们输入的数字，如昵称为“Dear-迪丽热巴”的id为1669879400
        self.filter = filter  # 取值范围为0、1，程序默认值为0，代表要爬取用户的全部微博，1代表只爬取用户的原创微博
        self.username = ''  # 用户名，如“Dear-迪丽热巴”
        self.weibo_num = 0  # 用户全部微博数
        self.weibo_num2 = 0  # 爬取到的微博数
        self.image_num = 0
        self.following = 0  # 用户关注数
        self.followers = 0  # 用户粉丝数
        self.weibo_content = []  # 微博内容
        self.weibo_image_count = []
        self.weibo_image_links = []
        self.weibo_reason = [] #微博转发原因
        self.publish_time = []  # 微博发布时间
        self.up_num = []  # 微博对应的点赞数
        self.retweet_num = []  # 微博对应的转发数
        self.comment_num = []  # 微博对应的评论数
        self.cookie = {"Cookie": my_cookie}
        self.max_page = max_page
        self.wait_time = wait_time

    # 获取用户昵称
    def get_username(self):
        try:
            url = "https://weibo.cn/%d/info" % (self.user_id)
            html = requests.get(url, cookies=self.cookie).content
            selector = etree.HTML(html)
            username = selector.xpath("//title/text()")[0]
            self.username = username[:-3]
            print (u"username:" + self.username).encode("utf-8")
        except Exception, e:
            print "Error: ", e
            traceback.print_exc()

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
            self.weibo_num = num_wb
            print "webo nums: " + str(self.weibo_num)

            # 关注数
            str_gz = selector.xpath("//div[@class='tip2']/a/text()")[0]
            guid = re.findall(pattern, str_gz, re.M)
            self.following = int(guid[0])
            print "followings: " + str(self.following)

            # 粉丝数
            str_fs = selector.xpath("//div[@class='tip2']/a/text()")[1]
            guid = re.findall(pattern, str_fs, re.M)
            self.followers = int(guid[0])
            print "followers: " + str(self.followers)

        except Exception, e:
            print "Error: ", e
            traceback.print_exc()

    # 获取用户微博内容及对应的发布时间、点赞数、转发数、评论数
    def get_weibo_info(self):
        try:
            url = "https://weibo.cn/u/%d?filter=%d&page=1" % (
                self.user_id, self.filter)
            html = requests.get(url, cookies=self.cookie).content
            selector = etree.HTML(html)
            if selector.xpath("//input[@name='mp']") == []:
                page_num = 1
            else:
                page_num = (int)(selector.xpath(
                    "//input[@name='mp']")[0].attrib["value"])
            pattern = r"\d+\.?\d*"
            pattern_full_article = re.compile(r'/comment/',re.I)
            pattern_one_image = re.compile(r'^http://weibo.cn/mblog/oripic',re.I)
            pattern_all_image = re.compile(r'^http://weibo.cn/mblog/picAll',re.I)
            pattern_one_image2 = re.compile(r'^/mblog/oripic',re.I)
            print "Total page num: " + str(page_num)
            if page_num > self.max_page:
                print "But you specified a max page num, it'll only download the first %d pages." % self.max_page
                page_num = self.max_page
            for page in range(1, page_num + 1):
                print "downloading page: %d" % (page)
                url2 = "https://weibo.cn/u/%d?filter=%d&page=%d" % (
                    self.user_id, self.filter, page)
                html2 = requests.get(url2, cookies=self.cookie).content
                selector2 = etree.HTML(html2)
                info = selector2.xpath("//div[@class='c']")
                if len(info) > 3:
                    for i in range(0, len(info) - 2):
                        # 微博内容
                        spans = info[i].xpath("div/span[@class='ctt']")
                        span_links = spans[0].xpath("a/@href")
                        if len(span_links) > 0 and pattern_full_article.match(span_links[len(span_links)-1]):
                            article_link = "http://weibo.cn" + span_links[len(span_links)-1]
                            article_html = requests.get(article_link, cookies=self.cookie).content
                            article_selector = etree.HTML(article_html)
                            article = article_selector.xpath("//div[@id='M_']/div/span[@class='ctt']")
                            weibo_content = article[0].xpath("string(.)").encode(
                                "utf-8", "ignore").decode(
                                "utf-8")
                            self.weibo_content.append(weibo_content)
                        else:
                            weibo_content = spans[0].xpath("string(.)").encode(
                                "utf-8", "ignore").decode(
                                "utf-8")
                            self.weibo_content.append(weibo_content)
                        #print (u"weibo content：" + weibo_content).encode("utf-8")

                        #images
                        links = info[i].xpath("div/a/@href")
                        image_links = []
                        for link in links:
                            if pattern_all_image.match(link):
                                image_links = []
                                image_html = requests.get(link, cookies=self.cookie).content
                                image_selector = etree.HTML(image_html)
                                sublinks = image_selector.xpath("//div/a/@href")
                                for sublink in sublinks:
                                    if pattern_one_image2.match(sublink):
                                        image_links.append("http://weibo.cn" + sublink)
                                break
                            elif pattern_one_image.match(link):
                                image_links.append(link)
                        self.weibo_image_count.append(len(image_links))
                        if len(image_links) > 0:
                            self.weibo_image_links = self.weibo_image_links + image_links

                        # 微博发布时间
                        str_time = info[i].xpath("div/span[@class='ct']")
                        str_time = str_time[0].xpath("string(.)").encode(
                            "utf-8", "ignore").decode(
                            "utf-8")
                        publish_time = str_time.split(u'来自')[0]
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
                        self.publish_time.append(publish_time)
                        #print (u"publish time：" + publish_time).encode("utf-8")

                        # 点赞数
                        str_infos = info[i].xpath("div/a/text()")
                        if len(str_infos) > 3:
                            str_zan = info[i].xpath("div/a/text()")[-4]
                            guid = re.findall(pattern, str_zan, re.M)
                            if len(guid) > 0:
                                up_num = int(guid[0])
                                self.up_num.append(up_num)
                            else:
                                self.up_num.append(0)
                        else:
                            self.up_num.append(0)

                        # 转发数
                        if len(str_infos) > 2:
                            retweet = info[i].xpath("div/a/text()")[-3]
                            guid = re.findall(pattern, retweet, re.M)
                            if len(guid) > 0:
                                retweet_num = int(guid[0])
                                self.retweet_num.append(retweet_num)
                            else:
                                self.retweet_num.append(0)
                        else:
                            self.retweet_num.append(0)

                        # 评论数
                        if len(str_infos) > 1:
                            comment = info[i].xpath("div/a/text()")[-2]
                            guid = re.findall(pattern, comment, re.M)
                            if len(guid) > 0:
                                comment_num = int(guid[0])
                                self.comment_num.append(comment_num)
                            else:
                                self.comment_num.append(0)
                        else:
                            self.comment_num.append(0)

                        self.weibo_num2 += 1
                print "Sleep for 5 seconds before accessing next page. Please wait..."
                time.sleep(self.wait_time)

            if not self.filter:
                print "total webo number: " + str(self.weibo_num2)
            else:
                print ("total weibo number: " + str(self.weibo_num) + ", original weibo number: " +
                       str(self.weibo_num2)
                       )
        except Exception, e:
            print "Error: ", e
            traceback.print_exc()

    # 将爬取的信息写入文件
    def write_txt(self):
        try:
            result_header = '''
            <!DOCTYPE html><html><head><link rel="stylesheet" type="text/css" href="css/lightbox.css">
            <link rel="stylesheet" type="text/css" href="css/style.css"><meta charset="UTF-8">
            <title>Weibo Backup</title></head><body>
            '''

            result_header = result_header + (u"<h1 style='text-align: center'>" + self.username + "</h1>" +
                      u"<p class='mycenter'><span>userid: " + str(self.user_id) +
                      u"</span><span>weibo num: " + str(self.weibo_num) +
                      u"</span><span>followings: " + str(self.following) +
                      u"</span><span>followers: " + str(self.followers) +
                      "</span></p><br>"
                      )
            result_header = result_header + '''
                <div id="hacker-list"><p class="mycenter"><input class="search" placeholder="Search by keyword or date" /></p><p class="mycenter">
                <button class="sort" data-sort="date">Sort by date</button><button class="sort" data-sort="upCount">Sort by up count</button>
                <button class="sort" data-sort="retweetCount">Sort by retweet count</button>
                <button class="sort" data-sort="commentCount">Sort by comment cout</button></p>
                <br><h3 id="weiboCount"></h3><h3 id="matchCount"></h3><ul class="list">
            '''
            image_link_index = 1
            result = ""
            for i in range(1, self.weibo_num2 + 1):
                text_head = (u"<li class='weibo'><p class='date'>" + self.publish_time[i - 1] +
                        u"</p><p class='content'>" + self.weibo_content[i - 1] + "</p><p>")

                #image anchors
                image_info = ""
                for j in range(0, self.weibo_image_count[i-1]):
                    image_info = image_info + "<a href='images/%d.jpg' data-lightbox='group%d'><img src='images/%d.jpg'></a>" % (image_link_index, i, image_link_index)
                    image_link_index += 1

                text_tail = (u"</p><p>up count：<span class='upCount'>" + str(self.up_num[i - 1]) +
                        u"</span>retweet count：<span class='retweetCount'>" + str(self.retweet_num[i - 1]) +
                        u"</span>comment count: <span class='commentCount'>" + str(self.comment_num[i - 1]) +
                        "</span></p></li>")
                result = result + text_head + image_info + text_tail

            result_tail = '''
                </ul></div><script src="js/jquery.js"></script><script src="js/lightbox.js"></script>
                <script src="js/list.js"></script><script src="js/script.js"></script></body></html>
                '''

            result = result_header + result + result_tail
            file_dir = os.path.split(os.path.realpath(__file__))[
                0] + os.sep + "weibo" + os.sep + str(self.user_id)
            if not os.path.isdir(file_dir):
                os.mkdir(file_dir)
            file_path = file_dir + os.sep + "index.html"
            f = open(file_path, "wb")
            f.write(result.encode("utf-8"))
            f.close()
            print (u"Have successfully written into the file:" + file_path).encode("utf-8")
        except Exception, e:
            print "Error: ", e
            traceback.print_exc()

    def download_images(self):
        if len(self.weibo_image_links) == 0:
            print "No images to download"
            return
        print "Start to download images"
        file_dir = os.path.split(os.path.realpath(__file__))[
            0] + os.sep + "weibo" + os.sep + str(self.user_id) + os.sep + "images"
        if not os.path.isdir(file_dir):
            os.mkdir(file_dir)
        index = 1
        for img_url in self.weibo_image_links:
            file_path = file_dir + os.sep + "%d.jpg" % index
            print "Trying to download image #%d" % index
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
            if index % 5 == 0:
                print "sleep for 5 seconds"
                time.sleep(self.wait_time)

    def moveFiles(self):
        print "Final step: copy some supporting files"
        src_dir = os.path.split(os.path.realpath(__file__))[0] + os.sep
        dest_dir = src_dir + "weibo" + os.sep + str(self.user_id) + os.sep
        copy_tree(src_dir+"js", dest_dir+"js")
        copy_tree(src_dir+"css", dest_dir+"css")
        copy_tree(src_dir+"images", dest_dir+"images")
    
    # 运行爬虫
    def start(self):
        try:
            self.get_username()
            self.get_user_info()
            self.get_weibo_info()
            self.write_txt()
            self.download_images()
            self.moveFiles()
            print u"\nCompleted successfully!"
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
        print "Read config parameters: max_page=%d, wait_time=%d" % (max_page, wait_time)
        filter = 1  # 值为0表示爬取全部微博（原创微博+转发微博），值为1表示只爬取原创微博
        wb = Weibo(user_id, my_cookie, max_page, wait_time, filter)  # 调用Weibo类，创建微博实例wb
        wb.start()  # 爬取微博信息
    except Exception, e:
        print "Error: ", e
        traceback.print_exc()


if __name__ == "__main__":
    main()
