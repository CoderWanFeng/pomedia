# -*- coding: utf-8 -*-
# @Time    : 2024/5/14 16:38
# @Author  : Kyln.Wu
# @Email   : kylnwu@qq.com
# @File    : to_weixin_draft.py
# @Software: PyCharm
import json
import os
import time
from io import BytesIO
import requests
import schedule
import urllib3
from PIL import Image

urllib3.disable_warnings()


def create_post_content(post_details):
    """
    定义微信公众号图文消息模板（这里举一个电影资料正文排版的例子）
    """
    centent_part = f"""\
<p>
<span style="color: #000000;">◎片　　名　{post_details.get('film_name')}</span><br>\
<span style="color: #000000;">◎年　　代　{post_details.get('year')}</span><br>\
<span style="color: #000000;">◎产　　地　{post_details.get('country')}</span><br>\
<span style="color: #000000;">◎类　　别　{post_details.get('category').strip('/').replace('/', ' / ')}</span><br>\
<span style="color: #000000;">◎上映日期　{post_details.get('release_date')}</span><br>\
<span style="color: #000000;">◎豆瓣链接　<a href="https://movie.douban.com/subject/{post_details.get('douban_id')}/" target="_blank">{post_details.get('douban_id')}</a></span><br>\
<span style="color: #000000;">◎导　　演　{'，'.join([director for director in post_details.get('directors')])}</span><br>\
<span style="color: #000000;">◎主　　演　{'，'.join([actor for actor in post_details.get('actors')])}</span><br>\
</p>
<p><span style="color: #000000;">◎简　　介</span></p>
<p><span style="color: #000000;">　　{post_details.get('intro')}</span></p>
<p><span style="color: #000000;">◎喜欢电影就点个关注吧。留言有惊喜哦！◎</span></p>
"""
    return centent_part


# ======================================
# 微信公众号发布消息代码开始
# ======================================
class ToWeixinDraft:
    def __init__(self):
        self.wx_access_token = self.get_access_token()

    def get_access_token(self):
        """
            获取公众号权限
            """
        APPID = '你的公众号appid，从公众号后台获取'
        APPSECRET = '你的公众号appsecret，从公众号后台获取'
        access_token_resp = requests.get(
            f'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}')
        json_obj = json.loads(access_token_resp.text)
        access_token = json_obj.get('access_token')
        print(f"access_token: {access_token}")

        return access_token

    # 获取公众号文章必须的title, digest, content, img_url，构造并返回多图文消息articles的结构
    def pack_articles(self):
        # 1 获取本次发布的所有文章的title, img_url, content, tags, intro, digest
        wx_title = f"你的文章标题"
        intro = create_post_content(post_details)
        # 摘要，取前100个字符
        digest = intro[:100]
        img_url = f"网络上的图片链接地址"
        # 获取推送电影海报
        base_path = f"图片保存的绝对路径，如：/www/wwwroot/to_weixin_draft"
        img_file_name = f'正文加载的图片文件名，如xxxx.jpg'
        save_path = os.path.join(base_path, img_file_name)

        # 2 上传封面获取封面id
        wx_fm_img_id = self.upd_fm_pic(save_path, img_file_name, img_url)

        # 3 上传正文图片到微信公众号,并获取返回的url地址
        wx_all_imgs_url = self.upd_imgs(save_path, img_file_name)

        # 4 用微信公众号返回的图片地址替换content里面的图片地址，获取最后要发布的正文内容
        wx_content_header = f"""\
        <p style="text-align: center;">
          <a href="{wx_all_imgs_url}" class="pirobox_gall" title="{wx_title}">\
            <img src="{wx_all_imgs_url}" alt="{wx_title}" width="500" height="700">\
          </a>
        </p>
        <p style="text-align: center;">
          {intro}
        </p>
        """
        # 构造多图文消息articles结构
        wx_content = wx_content_header
        articles_dict = self.create_post_dict(wx_title, digest, wx_content, wx_fm_img_id)
        # print(articles_lst)
        return articles_dict

    # 2 上传封面图片到微信公众号，并返回封面图片id
    def upd_fm_pic(self, save_path, img_file_name, img_url):
        headers = {
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36 SE 2.X MetaSr 1.0'
        }
        # 假设从网络上获取图片，如果是本地图片，省略以下requests代码
        resp = requests.get(img_url, headers=headers, verify=False)
        if resp.status_code == 200:
            # 使用BytesIO处理二进制数据
            image_data = BytesIO(resp.content)

            # 打开WebP图像文件
            image = Image.open(image_data)

            # 转换图像为JPG
            image_jpg = image.convert('RGB')

            # 保存转换后的图片到本地
            image_jpg.save(save_path, format='JPEG')

        url = f'https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={self.wx_access_token}&type=image'
        request_file = {
            'media': (img_file_name, open(save_path, 'rb'), 'image/jpeg')}
        vx_res = requests.post(url=url, files=request_file)
        obj = json.loads(vx_res.content)
        print(obj)
        return obj['media_id']

    # 3 上传正文图片到微信公众号，并返回正文图片网址
    def upd_imgs(self, save_path, img_file_name):
        vx_img_url = 'https://api.weixin.qq.com/cgi-bin/media/uploadimg'
        request_file = {
            'media': (img_file_name, open(save_path, 'rb'), 'image/jpeg')}
        data = {
            'access_token': self.wx_access_token
        }
        vx_res = requests.post(url=vx_img_url, files=request_file, data=data)
        obj = json.loads(vx_res.content)
        print(obj)
        return obj['url']

    # 4 构造多图文消息体的articles部分
    def create_post_dict(self, wx_title, digest, wx_content, wx_fm_img_id):
        """
        接口请求说明
        http
        请求方式：POST（请使用https协议）https://api.weixin.qq.com/cgi-bin/draft/add?access_token=ACCESS_TOKEN

        调用示例
        {
            "articles": [
                {
                    "title": TITLE,
                    "author": AUTHOR,
                    "digest": DIGEST,
                    "content": CONTENT,
                    "content_source_url": CONTENT_SOURCE_URL,
                    "thumb_media_id": THUMB_MEDIA_ID,
                    "show_cover_pic": 1,
                    "need_open_comment": 0,
                    "only_fans_can_comment": 0
                }
                // 若新增的是多图文素材，则此处应还有几段articles结构
        ]
        }
        """
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

    # post到公众号草稿箱
    def upd_post2cgx(self, data):
        url = 'https://api.weixin.qq.com/cgi-bin/draft/add?access_token=' + self.wx_access_token
        vx_res = requests.post(url=url, data=json.dumps(data, ensure_ascii=False).encode("utf-8"))
        res_obj = json.loads(vx_res.content)
        print(res_obj)
        if 'errmsg' in res_obj:
            print("公众号上传失败。")
            return False
        else:
            print("公众号上传成功。")
            return True


# 运行主函数
def do_job():
    try:
        # 先实例化上传到微信公众号的类
        do_weixin_draft = ToWeixinDraft()
        # 组织文章内容
        data = do_weixin_draft.pack_articles()
        # 上传到微信公众号草稿箱
        res_msg = do_weixin_draft.upd_post2cgx(data)
        n = 1
        # 如果上传失败，尝试3次，每次间隔159秒
        while not res_msg:
            res_msg = do_weixin_draft.upd_post2cgx(data)
            n += 1
            time.sleep(159)
            if n == 3:
                print('公众号发布尝试3次失败，退出。')
                break
    except Exception as e:
        print(e)


if __name__ == '__main__':
    # 部署情况
    # schedule.every(10).minutes.do(do_job)  # 部署每10分钟执行一次do_job()函数的任务
    # schedule.every().hour.do(do_job)  # 部署每×小时执行一次do_job()函数的任务
    schedule.every().day.at("10:30").do(do_job)  # 部署在每天的10:30执行do_job()函数的任务
    # schedule.every().monday.do(do_job)  # 部署每个星期一执行do_job()函数的任务
    # schedule.every().wednesday.at("13:15").do(do_job)  # 部署每周三的13：15执行函数的任务

    while True:
        schedule.run_pending()
        time.sleep(1)
