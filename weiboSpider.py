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


class Weibo:
    cookie = {"Cookie": "ALF=1511292190; SCF=Ao8FN3T73o955m8rh4WVlZGsDpMYvW3n5xoJ_YijU7myixsdOK4V3ywzGht1nH2z5X3WsF7uD4eCeWFPFvdvrts.; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WW848PI.Op2TZ2OZN0dhmri5JpX5KMhUgL.Foe7e050S0n01hM2dJLoIpW2IgDuMNxEqHvTMrH0Ic8j; _T_WM=4c97dd7f3d4d7a76dfffe9b223cbeb9b; SUB=_2A2506IYMDeRhGeVO6FIS9ybPwzuIHXVUEipErDV6PUJbkdBeLVDQkW1bEjRoiGvmRoWP9BaoxrwhFgrxCQ..; SUHB=0z1AL6Yu7J5YXN; SSOLoginState=1508701788"}  # 将your cookie替换成自己的cookie

    # Weibo类初始化
    def __init__(self, user_id, filter=0):
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

    # 获取用户昵称
    def get_username(self):
        try:
            url = "https://weibo.cn/%d/info" % (self.user_id)
            html = requests.get(url, cookies=self.cookie).content
            selector = etree.HTML(html)
            username = selector.xpath("//title/text()")[0]
            self.username = username[:-3]
            #print (u"username: " + self.username).encode("utf-8")
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
            #for page in range(1, page_num + 1):
            for page in range(1, 2):
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
                        str_zan = info[i].xpath("div/a/text()")[-4]
                        guid = re.findall(pattern, str_zan, re.M)
                        up_num = int(guid[0])
                        self.up_num.append(up_num)
                        #print "up num: " + str(up_num)

                        # 转发数
                        retweet = info[i].xpath("div/a/text()")[-3]
                        guid = re.findall(pattern, retweet, re.M)
                        retweet_num = int(guid[0])
                        self.retweet_num.append(retweet_num)
                        #print "retweet num: " + str(retweet_num)

                        # 评论数
                        comment = info[i].xpath("div/a/text()")[-2]
                        guid = re.findall(pattern, comment, re.M)
                        comment_num = int(guid[0])
                        self.comment_num.append(comment_num)
                        #print "comment num: " + str(comment_num)

                        self.weibo_num2 += 1
                print "Sleep for 5 seconds before accessing next page. Please wait..."
                time.sleep(5)

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
            if self.filter:
                result_header = u"\n\nOriginal Weibo Content： \n"
            else:
                result_header = u"\n\nWeibo Content：\n"
            result = (u"User Info\nusername：" + self.username +
                      u"\nuserid:" + str(self.user_id) +
                      u"\nweibo num:" + str(self.weibo_num) +
                      u"\nfollowings:" + str(self.following) +
                      u"\nfollowers:" + str(self.followers) +
                      result_header
                      )
            image_link_index = 0
            for i in range(1, self.weibo_num2 + 1):
                text = (str(i) + ":" + self.weibo_content[i - 1] + "\n" +
                        u"images count: " + str(self.weibo_image_count[i-1]) + "\n"
                        u"publish time：" + self.publish_time[i - 1] + "\n" +
                        u"up num：" + str(self.up_num[i - 1]) +
                        u"   retweet num：" + str(self.retweet_num[i - 1]) +
                        u"   comment num：" + str(self.comment_num[i - 1]) + "\n\n"
                        )
                image_info = ""
                for j in range(0, self.weibo_image_count[i-1]):
                    image_info = image_info + self.weibo_image_links[image_link_index] + "\n"
                    image_link_index += 1
                result = result + text + image_info
            file_dir = os.path.split(os.path.realpath(__file__))[
                0] + os.sep + "weibo"
            if not os.path.isdir(file_dir):
                os.mkdir(file_dir)
            file_path = file_dir + os.sep + "%d" % self.user_id + ".txt"
            f = open(file_path, "wb")
            f.write(result.encode("utf-8"))
            f.close()
            print (u"Have successfully written into the file:" + file_path).encode("utf-8")
        except Exception, e:
            print "Error: ", e
            traceback.print_exc()

    # 运行爬虫
    def start(self):
        try:
            self.get_username()
            self.get_user_info()
            self.get_weibo_info()
            self.write_txt()
            print u"\nCompleted successfully!"
            print "==========================================================================="
        except Exception, e:
            print "Error: ", e


def main():
    try:
        # 使用实例,输入一个用户id，所有信息都会存储在wb实例中
        user_id = 5822702445  # 可以改成任意合法的用户id（爬虫的微博id除外）
        filter = 1  # 值为0表示爬取全部微博（原创微博+转发微博），值为1表示只爬取原创微博
        wb = Weibo(user_id, filter)  # 调用Weibo类，创建微博实例wb
        wb.start()  # 爬取微博信息
        print (u"username:" + wb.username).encode("utf-8")
        print "Saved weibo num:" + str(wb.weibo_num2)
    except Exception, e:
        print "Error: ", e
        traceback.print_exc()


if __name__ == "__main__":
    main()
