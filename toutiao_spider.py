# -*- coding:utf-8 -*-
import requests
import pymongo
from urllib.parse import urlencode
from requests.exceptions import RequestException
import json
from bs4 import BeautifulSoup
import re, os
from config_toutiao import *
from hashlib import md5
from multiprocessing import Pool

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]

def get_page_index(offset,keyword):
    data = {
        'offset': offset,
        'format': 'json',
        'keyword': keyword,
        'autoload': 'true',
        'count': '20',
        'cur_tab': 3,
        'from': 'gallery',
    }
    header = {
        'User-Agent': 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      + '(KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
    }
    url = 'https://www.toutiao.com/search_content/?' + urlencode(data)
    response = requests.get(url,headers = header)
    try:
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求出错')
        return None

def parse_page_index(html):
    data = json.loads(html)
    if data and 'data' in data.keys():
        for item in data.get('data'):
            yield item.get('article_url')

def get_page_detail(url):
    header = {
        'User-Agent': 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      + '(KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
    }
    response = requests.get(url, headers = header)
    try:
        if response.status_code == 200:
            return response.text
        return None
    except RequestException:
        print('请求详细页出错')
        return None

def parse_page_detail(html, url):
    soup = BeautifulSoup(html, 'lxml')
    title = soup.select('title')[0].get_text()
    pattern = re.compile('JSON.parse(.*)siblingList', re.S)
    result = re.search(pattern, html)
    if result:
        datas = result.group(1).strip()[:-1]
        data = datas.replace('\\', '')[:-2][2:]
        data = json.loads(data)
        if data and 'sub_images' in data.keys():
            sub_images = data.get('sub_images')
            images = [item.get('url') for item in sub_images]
            for image in images:
                download_image(image)
            return {
                'title': title,
                'url': url,
                'images': images,
            }

def save_to_mongo(result):
    if db[MONGO_TABLE].insert(result):
        print('存储到MongoDB',result)
        return True
    return False

def download_image(url):
    print('正在下载',url)
    header = {
        'User-Agent': 'user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      + '(KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
    }
    response = requests.get(url, headers=header)
    try:
        if response.status_code == 200:
            save_image(response.content)
        return None
    except RequestException:
        print('请求图片出错')
        return None

def save_image(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(), md5(content).hexdigest(),'jpg')
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content)


def main(offset):
    html = get_page_index(offset,KEYWORD)
    for url in parse_page_index(html):
        html = get_page_detail(url)
        if html:
            result =parse_page_detail(html, url)
            save_to_mongo(result)

if __name__ == '__main__':
    groups = [x*20 for x in range(GROUP_START, GROUP_END+1)]
    pool = Pool()
    pool.map(main, groups)