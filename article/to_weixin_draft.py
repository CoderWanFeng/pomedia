# -*- coding: utf-8 -*-
# @Time    : 2023/7/6 9:47
# @Author  : Kyln.Wu
# @Email   : kylnwu@qq.com
# @File    : to_weixin_draft.py
# @Software: PyCharm
import json
import os
import re
import time
import requests
from lxml import html
from lxml.html import tostring

etree = html.etree


class ToWeixin:
    """
    爬取资料和图片，上传到公众号草稿箱的类
    """

    def __init__(self):
        APPID = '你的公众号APPID'
        APPSECRET = '你的公众号SECRETKEY'
        access_token_resp = requests.get(
            f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}')
        json_obj = json.loads(access_token_resp.text)
        self.access_token = json_obj.get('access_token')
        if not self.access_token:
            print("access_token is Null!")

    def get_movie_details(self, start_id, end_id):
        """
        爬取需要发布到公众号的信息（主要是主图和正文内容），根据自己的需要替换这个函数
        返回一个嵌套字典的列表
        """
        movie_infos_lst = []
        for k in range(int(start_id), int(end_id) + 1):
            movie_infos_dict = {}
            url = f"http://www.bd51.net/index/mdetail/index.html?id={k}"
            resp = requests.get(url)
            code = resp.apparent_encoding  # 获取url对应的编码格式
            resp.encoding = code
            html_code = resp.text
            movie_infos_html = etree.HTML(html_code)
            movie_cn_name = movie_infos_html.xpath("/html/body/div[3]/div[1]/div[2]/div[1]/div[2]/div/h3/text()")[0]
            movie_year = re.findall('\((\d+)\)', movie_cn_name)[0]
            part_pic_url = movie_infos_html.xpath('/html/body/div[3]/div[1]/div[2]/div[1]/div[2]/img/@src')[0]
            pic_url = f"http://www.bd51.net{part_pic_url}"
            imdb_rate = self.get_imdb_rate(k)
            div_tag1 = movie_infos_html.xpath("/html/body/div[3]/div[1]/div[2]/div[1]/div[2]/div")[0]
            div_tag2 = movie_infos_html.xpath("/html/body/div[3]/div[1]/div[2]/div[2]")[0]
            digest = movie_infos_html.xpath('/html/body/div[3]/div[1]/div[2]/div[2]/div[2]/p//text()')[0]
            html1 = tostring(div_tag1, encoding=code).decode(code).replace('\n', '')
            html1 = html1.replace('<h3>', '<p><strong>').replace('</h3>', '</strong></p>')
            html1 = html1.replace('首映日期：</strong></span>', f'上映年份：</strong>{movie_year}</span>')
            html1 = html1.replace('<p class="imob">0</p>', f'<p><img src="{pic_url}"></p>')
            html1 = html1.replace(' 00:00:00', '')
            html1 = html1.replace('</span><span>', '</span><br><span>')
            imdb_partern = re.compile('(人气：</strong>\d+</span>)', re.S)
            html1 = re.sub(imdb_partern, f'IMDB：</strong>{imdb_rate}</span>', html1)
            html2 = tostring(div_tag2, encoding=code).decode(code).replace('\n', '')
            html2_partern = re.compile('(<img.*?g">)', re.S)
            html2 = re.sub(html2_partern, '', html2)
            html2 = html2.replace('剧情介绍', '</strong>剧情介绍</span>')
            # print(html1)
            # print(html2)
            wx_content = html1 + html2

            movie_infos_dict['中文名'] = movie_cn_name
            movie_infos_dict['海报'] = pic_url
            movie_infos_dict['影片简介'] = wx_content
            movie_infos_dict['摘要'] = digest
            movie_infos_lst.append(movie_infos_dict)
            # print(movie_detail)
            time.sleep(1)
        return movie_infos_lst

    def get_imdb_rate(self, id):
        """
        :param id: 影片ID，接收影片id，到影片列表页进行搜索，匹配豆瓣评分
        :return: 如果匹配到了，就结束搜索，返回评分值
        """
        for j in range(1, 10):
            # 遍历9页搜索影片
            url = f"http://www.bd51.net/index/mlist/index.html?page={j}"
            res = requests.get(url).text
            time.sleep(3)
            index_html = etree.HTML(res)
            try:
                search_xpath = index_html.xpath(f'//*[@id="{id}"]')
                if search_xpath:
                    imdb_rate = index_html.xpath(f'//*[@id="{id}"]/td[4]/p/text()')[0]
                    # print(imdb_rate)
                    return imdb_rate
            except:
                print(f"ID：{id}没找到。")

    # 1 获取公众号文章必须的title, digest, content, img_url四个字段，构造并返回多图文消息articles的结构
    def pack_articles_list(self, movie_details):
        # 获取本次发布的所有文章的title, img_url, content, tags, intro, digest
        wx_title = movie_details.get('中文名') + ' 更新上架'
        digest = movie_details.get('摘要')[:100]
        # base_folder = '/www/wwwroot/api/' + time.strftime('%Y-%m-%d')
        base_folder = time.strftime('%Y-%m-%d')
        file_name = movie_details.get('海报').rsplit('/', 1)[1]
        print(file_name)
        file_path = os.path.join(base_folder, file_name)
        if not os.path.exists(base_folder):
            os.makedirs(base_folder)
        # 2 上传封面获取封面id
        wx_fm_img_id, file_path = self.upd_fm_pic(file_name, file_path)
        # 3 上传正文图片到微信公众号,并获取返回的url地址
        wx_all_imgs_url = self.upd_imgs(file_path, file_name)
        # 4 用微信公众号返回的图片地址替换content里面的图片地址，获取最后要发布的正文内容
        img_url_pattern = re.compile('(https?://[a-zA-Z0-9.?/%-_]*.jpg)', re.S)
        content = movie_details.get('影片简介')
        wx_content = re.sub(img_url_pattern, wx_all_imgs_url, content)
        # print(wx_content)
        # 构造多图文消息articles结构
        articles_dict = self.create_post_dict(wx_title, digest, wx_content, wx_fm_img_id)
        # print(articles_lst)
        return articles_dict

    # 2 上传封面图片到微信公众号，并返回封面图片id和本地图片绝对路径
    def upd_fm_pic(self, file_name, file_path):
        try:
            url = f'https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={self.access_token}&type=image'
            request_file = {
                'media': (file_name, open(file_path, 'rb'), 'image/jpeg')}
            vx_res = requests.post(url=url, files=request_file)
            obj = json.loads(vx_res.content)
            print(obj)
            return obj['media_id'], file_path
        except Exception as e:
            print(e)

    # 3 上传正文图片到微信公众号，并返回正文图片网址
    def upd_imgs(self, file_path, file_name):
        try:
            vx_img_url = 'https://api.weixin.qq.com/cgi-bin/media/uploadimg'
            request_file = {
                'media': (file_name, open(file_path, 'rb'), 'image/jpeg')}
            data = {
                'access_token': self.access_token
            }
            vx_res = requests.post(url=vx_img_url, files=request_file, data=data)
            obj = json.loads(vx_res.content)
            print(obj)
            return obj['url']
        except Exception as e:
            print(e)

    # 4 构造多图文消息体的articles部分
    def create_post_dict(self, wx_title, digest, wx_content, wx_fm_img_id):
        articles_dict = {
            "title": wx_title,
            "author": '',
            "digest": digest,
            "content": wx_content,
            "show_cover_pic": 1,
            "need_open_comment": 0,
            "only_fans_can_comment": 1,
            "thumb_media_id": wx_fm_img_id
        }
        return articles_dict

    # 5.2 把文章分组并上传到草稿箱
    def to_wx_draft(self, movie_datas_list):
        # ==========微信公众号同步发布===========
        # 如果爬取资料少于5篇
        if len(movie_datas_list) < 5:
            # 构造上传多图文消息的data
            data = {
                "articles": [self.pack_articles_list(movie_details) for movie_details in movie_datas_list]
            }
            # print(data)
            # 上传到草稿箱
            self.upd_post2cgx(data)
            print("上传公众号完成！")
        else:
            # 如果爬取资料大于5篇，则每5篇合成一篇发送到草稿箱
            for i in range(0, len(movie_datas_list), 5):
                # 构造上传多图文消息的data
                data = {
                    "articles": [self.pack_articles_list(movie_details) for movie_details in movie_datas_list[i:i + 5]]
                }
                # print(data)
                # 上传到草稿箱
                self.upd_post2cgx(data)
            print("上传公众号完成！")
        return

    # 5.1 post到公众号草稿箱
    def upd_post2cgx(self, data):
        try:
            url = 'https://api.weixin.qq.com/cgi-bin/draft/add?access_token=' + self.access_token
            vx_res = requests.post(url=url, data=json.dumps(data, ensure_ascii=False).encode("utf-8"))
            obj = json.loads(vx_res.content)
            # print(obj)
            return obj['media_id']
        except Exception as e:
            print(e)


if __name__ == '__main__':
    do_job = ToWeixin()
