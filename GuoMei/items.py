# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class GuomeiItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    _id = scrapy.Field()
    # 关键字
    keyword = scrapy.Field()
    # 商品总数
    totalCount = scrapy.Field()
    # 商品信息
    product_info = scrapy.Field()


# 店铺信息
class GuoMeiShop(scrapy.Item):
    """
    关于店铺信息中一些字段的说明:
    "score":"5.0",  -----------> 综合评价
    "shopTag":2,    -----------> 1 : 是联营 2 : 是自营
    "serv":"5.0",   -----------> 服务质量
    "icon":"//gfs11.gomein.net.cn/T1K3YbBXZT1RCvBVdK.png",  -----------> 商铺头像
    "match":"5.0",  -----------> 商品描述
    "name":"小米官方旗舰店",   -----------> 商铺名称
    "shopId":"10000988",    -----------> 商铺 id
    "addr":"",  -----------> 商铺地址
    "dataCode":"9000000700-1_1_1",  ----------->
    "isSelf":1, ----------->
    "speed":"5.0"   -----------> 发货速度
    """
    # mongodb 的id
    _id = scrapy.Field()
    # 关键字
    keyword = scrapy.Field()
    # 店铺总数
    totalCount = scrapy.Field()
    # 店铺信息
    shop_info = scrapy.Field()
