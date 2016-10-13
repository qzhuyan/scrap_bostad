# -*- coding: utf-8 -*-
import scrapy
import time
from urlparse import urlparse
from urlparse import parse_qs
import re


class HittaSpider(scrapy.Spider):
    name = "hitta"
    allowed_domains = ["hitta.se"]
    start_urls = (
        'https://www.hitta.se/s%C3%B6k?vad=Bostadsr%C3%A4ttsf%C3%B6reningar+Stockholm',
    )

    def parse(self, response):
        for href in response.css('[class="link--neutral result-row__link"]::attr(href)'):
            company_page = response.urljoin(href.extract())
            yield scrapy.Request(company_page, callback=self.parse_company_page)

        time.sleep(2)
        # we might get next_page, one for last page one for next page
        # the 1st page has no 'last page', that is why we use result-list__pagination
        # spider is smart enough to skip already scraped page
        for next_page in response.css('[class="result-list__pagination"] a::attr(href)'):
            next_page = response.urljoin(next_page.extract())
            print "we can follow next page which is %s" % next_page
            yield scrapy.Request(next_page, callback=self.parse)

    def parse_company_page(self, response):
        orgNo = get_orgnum(response)
        groups = response.css('[class=group]')

        web = response.css('[class="plain item-details__web-links"]')

        try:
            maploc = response.css('[class="address-go-to-map-container plain"]')[0].css("a::attr(href)").extract_first()
            latlong = parse_qs(urlparse(maploc).query)[u'sat']
        except:
            print "not able to get latlong "
            latlong = None;

        if len(web) > 0:
            web = web[0].css('a::attr("href")').extract_first()

        phone_num = get_phone_num(response)

        result =  {
            'name':           response.css('[itemprop="name"]::text').extract_first(),
            'phone':          phone_num,
            'address':        to_addr(groups, 1),
            'mail':           to_addr(groups, 2),
            'web':            web,
            'map':            latlong,
            'brf_key':        orgNo
        }

        if orgNo is not None:
            next_req = scrapy.Request("https://api.hitta.se/info/v3/brf/" + orgNo, callback=self.parse_brf_info, meta={'item': result})
            yield next_req
        else:
            yield result


    def parse_brf_info(self, response):
        item = response.meta['item']
        try:
            item['extra'] = response.body_as_unicode()
            yield item
        except:
            yield item



def get_phone_num(res):
    try:
        return res.css('[class="print-phone-number"]::text').extract_first()
    except:
        return None

def to_addr(group, x):
    try:
        sel = group[x]
        return {
            'streetAddress':  sel.css('[itemprop="streetAddress"]::text').extract_first(),
            'postalCode':     sel.css('[itemprop="postalCode"]::text').extract_first(),
            'addressLocality':sel.css('[itemprop="addressLocality"]::text').extract_first()
        }
    except:
        return None


def get_orgnum(res):
    try:
        div = res.css('[class="secondary"]').extract_first()
        for l in div.split('\n'):
            match =  re.match('.*orgNo:(.*),', l)
            if match:
               return match.group(1).strip()
        return None
    except:
        return None
