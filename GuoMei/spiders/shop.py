"""
此爬虫是根据关键字采集国美的店铺信息
响应的数据为 json 格式
"""
import json
import os

import scrapy
from scrapy.exceptions import CloseSpider
from scrapy.signals import spider_closed
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy_redis.spiders import RedisSpider
from twisted.internet.error import TCPTimedOutError, DNSLookupError

from GuoMei.items import GuoMeiShop


class GuoMeiShopSpider(RedisSpider):
    # 爬虫名称
    name = 'shopSpider'
    # 启动命令
    redis_key = 'GuoMeiShopSpider:items'
    # 配置信息
    custom_settings = dict(
        ITEM_PIPELINES={
            'GuoMei.pipelines.ShopInfoPipeline': 300,
        }
    )

    def __init__(self, settings):
        super(GuoMeiShopSpider, self).__init__()
        # 任务文件列表
        self.keyword_file_list = os.listdir(settings.get("KEYWORD_PATH"))
        # 店铺请求的URL 10 ----> 每页显示数量   2 -----> 页号
        self.shop_url = 'https://apis.gome.com.cn/p/mall/10/{page}/{keyword}?from=search'
        # headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/'
                          '537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36',
            # '': '',
        }

    def parse_err(self, failure):
        """
        异常处理函数
        :param failure:
        :return:
        """
        if failure.check(TimeoutError, TCPTimedOutError, DNSLookupError):
            # 失败的请求
            request = failure.request
            # 失败请求重新加入请求队列
            self.server.rpush(self.redis_key, request)

        if failure.check(HttpError):
            # 响应
            response = failure.value.response
            # 失败请求重新加入请求队列
            self.server.rpush(self.redis_key, response.url)
        return

    def start_requests(self):
        """
        循环读取文件列表,生成初始请求
        :return:
        """
        if not self.keyword_file_list:
            # 抛出异常,并关闭爬虫
            raise CloseSpider('需要关键字文件')
        for keyword_file in self.keyword_file_list:
            # 循环获取关键字文件路径
            file_path = os.path.join(self.settings.get("KEYWORD_PATH"), keyword_file)
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                for keyword in f.readlines():
                    # 消除关键字末尾的空白字符
                    keyword = keyword.strip()
                    # 发起请求
                    yield scrapy.Request(url=self.shop_url.format(page=str(1), keyword=keyword), callback=self.parse,
                                         errback=self.parse_err, meta={'keyword': keyword})

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        # 配置信息
        settings = crawler.settings
        # 爬虫信息
        spider = super(GuoMeiShopSpider, cls).from_crawler(crawler, settings, *args, **kwargs)
        # 终止爬虫信号
        crawler.signals.connect(spider.spider_closed, signal=spider_closed)
        # 返回 spider
        return spider

    def spider_closed(self, spider):
        """
        自定义爬虫关闭执行的操作
        :param spider:
        :return:
        """
        self.logger.info('Spider closed : %s', spider.name)
        # 视具体的情况添加如下两个文件的操作方法
        # spider.record_file.write("]")
        # spider.record_file.close()

    def parse(self, response):
        if response.status == 200:
            print(response.text)
            # 关键字
            keyword = response.meta['keyword']
            # json ---> dict
            res = json.loads(response.text, encoding='utf-8')
            # 总页数
            totalPage = res.get('totalPage')
            # 当前页号
            currentPage = res.get('currentPage')
            # 搜索结果总数
            totalCount = res.get('totalCount')
            # 店铺信息列表
            shopList = res.get('shopList')
            if shopList:
                for shop in shopList:
                    # item
                    item = GuoMeiShop()
                    # 关键字
                    item['keyword'] = keyword
                    # 店铺总数
                    item['totalCount'] = totalCount
                    # 店铺信息
                    item['shop_info'] = shop
                    yield item
            if int(currentPage) < int(totalPage):
                # 下一页
                yield scrapy.Request(url=self.shop_url.format(page=int(currentPage) + 1, keyword=keyword),
                                     callback=self.parse, errback=self.parse_err, meta=response.meta)
