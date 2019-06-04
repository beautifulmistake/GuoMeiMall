"""
此爬虫是根据关键字采集国美商城的商品信息
将最中结果直接存入 mongodb 之中
"""
import json
import os
import requests
import scrapy
from scrapy.exceptions import CloseSpider
from scrapy.signals import spider_closed
from scrapy.spidermiddlewares.httperror import HttpError
from scrapy_redis.spiders import RedisSpider
from twisted.internet.error import TCPTimedOutError, DNSLookupError
from GuoMei.items import GuomeiItem


class GuoMeiSpider(RedisSpider):
    # 爬虫名称
    name = "GuoMei"
    # 启动命令, 默认命名方法位 Spider类名 + items
    redis_key = "GuoMeiSpider:items"

    def __init__(self, settings):
        super(GuoMeiSpider, self).__init__()
        self.keyword_file_list = os.listdir(settings.get("KEYWORD_PATH"))
        # 搜索的URL
        self.search_url = 'https://search.gome.com.cn/search?search_mode=normal&reWrite=true&' \
                          'question={keyword}&searchType=goods&&page={page}&type=json&aCnt=0&reWrite=true'
        # 请求头
        self.headers = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/'
                          '537.36 (KHTML, like Gecko) Chrome/72.0.3626.109 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
            # 'Referer': 'https://search.gome.com.cn/search
            # ?question=%E5%B0%8F%E7%B1%B3&searchType=goods&search_mode=normal&reWrite=true'
        }
        # 动态地在请求头中添加 Referer
        self.referer = "https://search.gome.com.cn/search?question={keyword}" \
                       "&searchType=goods&page=1&search_mode=normal&reWrite=true"
        # 请求价格的URL
        self.price_url = "https://ss.gome.com.cn/search/v1/price/single/{pId}/{skuId}/11010000/flag/item/"

    def parse_err(self, failure):
        """
        异常处理函数,请求失败的 Request 对象 将按照自定义的方式进行处理
        :param failure:
        :return:
        """
        if failure.check(TimeoutError, TCPTimedOutError, DNSLookupError):
            # 失败的请求
            request = failure.request
            # 将失败的请求重新加入请求队列
            self.server.rpush(self.redis_key, request)

        if failure.check(HttpError):
            # 获取响应
            response = failure.value.response
            # 重新加入请求队列
            self.server.rpush(self.redis_key, response.url)
        return

    def start_requests(self):
        """
        循环读取文件列表,生成初始请求
        :return:
        """
        # 判断关键字文件是否存在
        if not self.keyword_file_list:
            # 抛出异常并关闭爬虫
            raise CloseSpider("需要关键字文件")
        for keyword_file in self.keyword_file_list:
            # 循环读取关键字文件
            file_path = os.path.join(self.settings.get("KEYWORD_PATH"), keyword_file)
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                for keyword in f.readlines():
                    # 消除关键字末尾的空白字符
                    keyword = keyword.strip()
                    # 发起请求
                    self.headers.update({'Referer': self.referer.format(keyword=keyword)})
                    # print("查看更新后的headers:", self.headers)
                    yield scrapy.Request(url=self.search_url.format(keyword=keyword, page=str(1)),
                                         headers=self.headers,
                                         callback=self.parse, errback=self.parse_err, meta={'keyword': keyword})

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        # 配置信息
        settings = crawler.settings
        # 爬虫信息
        spider = super(GuoMeiSpider, cls).from_crawler(crawler, settings, *args, **kwargs)
        # 终止爬虫信号
        crawler.signals.connect(spider.spider_closed, signal=spider_closed)
        # 返回spider 不然无法运行 start_requests 方法
        return spider

    def spider_closed(self, spider):
        """
        自定义的爬虫关闭时执行的操作
        :param spider:
        :return:
        """
        # 输出日志,提示关闭爬虫
        self.logger.info('Spider closed: %s', spider.name)
        # 视具体的情况添加如下两个文件的操作方法
        # spider.record_file.write("]")
        # spider.record_file.close()

    def parse(self, response):
        """
        列表页解析函数
        :param response:
        :return:
        """
        if response.status == 200:
            # print(response.text)
            keyword = response.meta['keyword']
            res = json.loads(response.text, encoding='utf-8')
            # 搜索结果信息,总页数,当前页数,总条数
            pageNumber = res.get('content').get('pageBar').get('pageNumber')    # 当前地页号
            totalPage = res.get('content').get('pageBar').get('totalPage')  # 总页数
            totalCount = res.get('content').get('pageBar').get('totalCount')    # 搜索总数
            # 获取商品地列表
            products = res.get('content').get('prodInfo').get('products')   # 获取所有商品项
            if products:
                for product in products:
                    # 创建 item
                    item = GuomeiItem()
                    product_info = product
                    # 商品 id
                    pId = product.get('pId')
                    # skuId
                    skuId = product.get('skuId')
                    # 获取价格
                    price_dict = GuoMeiSpider.parse_price(self.price_url.format(pId=pId, skuId=skuId))
                    price = price_dict.get('result').get('price')
                    product_info.update({'price': price})
                    item['totalCount'] = totalCount
                    item['keyword'] = keyword
                    item['product_info'] = product_info
                    yield item
            if int(pageNumber) < int(totalPage):
                page = int(pageNumber) + 1
                yield scrapy.Request(url=self.search_url.format(keyword=keyword, page=str(page)), headers=self.headers,
                                     callback=self.parse, errback=self.parse_err, meta={'keyword': keyword})

    @staticmethod
    def parse_price(url):
        """
        请求商品价格
        :param url:
        :return:
        """
        res = requests.get(url=url)
        if res.status_code == 200:
            return json.loads(res.text, encoding='utf-8')
