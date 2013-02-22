# -*- coding: utf-8 -*-

import gevent.monkey
gevent.monkey.patch_all()

import gevent
from gevent import Timeout

import urllib
import urllib2
import cookielib
import functools
from lxml import etree


class TooLong(Exception):
    pass


class RenRen(object):
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.login()


    def login(self):
        url  = 'http://www.renren.com/ajaxLogin/login'
        data = {
            'email': self.email,
            'password': self.password,
            'origURL': 'http://www.renren.com/home',
            'domain': 'renren.com',
        }

        data = urllib.urlencode(data)

        cookie = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
        urllib2.install_opener(self.opener)

        request = urllib2.Request(url, data=data)
        res = urllib2.urlopen(request)


    def view_page(self, uid):
        url = 'http://www.renren.com/{0}/profile'.format(uid)
        res = self.opener.open(url)
        return uid, res.code, res.geturl()


    def get_friends(self, uid):
        URL = 'http://friend.renren.com/GetFriendList.do?curpage={0}&id=' + str(uid)
        # first_html = urllib2.urlopen(URL.format(0))
        first_html = self.opener.open(URL.format(0))

        parse = etree.HTMLParser()
        # tree = etree.parse(first_html, parse)
        tree = etree.fromstring(first_html.read(), parse)
        whole_friends_amount = tree.xpath('//div[@id="toc"]/p[1]/span')[0].text
        whole_friends_amount = int(whole_friends_amount)

        print whole_friends_amount

        whole_page, _rest = divmod(whole_friends_amount, 20)
        if _rest > 0:
            whole_page += 1


        friends_xpath = '//div[@id="list-results"]//li/p/a/@href'
        all_friends = []

        first_page_friends = [f.split('=')[1] for f in tree.xpath(friends_xpath)]
        all_friends.extend(first_page_friends)

        def _timeout(t):
            def deco(func):
                @functools.wraps(func)
                def wrap(*args, **kwargs):
                    try:
                        with Timeout(t, TooLong):
                            return func(*args, **kwargs)
                    except TooLong:
                        print 'tool long, args=', args
                        return []
                return wrap
            return deco


        @_timeout(6)
        def _get(p):
            print 'get page', p
            # html = urllib2.urlopen(URL.format(p))
            html = self.opener.open(URL.format(p))
            # print html.read()
            # tree = etree.parse(html, parse)
            tree = etree.fromstring(html.read(), parse)
            res = [f.split('=')[1] for f in tree.xpath(friends_xpath)]
            print p
            print res
            return res

        # this is sync version
        # for i in range(1, whole_page):
        #     all_friends.extend(_get(i))


        # this is async version
        workers = [gevent.spawn(_get, i) for i in range(1, whole_page)]
        gevent.joinall(workers)

        print 'joinall done'

        for w in workers:
            all_friends.extend(w.value)


        # print all_friends
        print len(all_friends) == len(set(all_friends))
        print len(all_friends), whole_friends_amount







with open('account', 'r') as f:
    data = f.readlines()
    email = data[0].rstrip('\n')
    password = data[1].rstrip('\n')


r = RenRen(email, password)

# r.get_friends(256089759)
r.get_friends(252572048)

# workers = [
#     gevent.spawn(r.view_page, 252572048),
#     gevent.spawn(r.view_page, 259057317),
#     gevent.spawn(r.view_page, 256089759),
#     gevent.spawn(r.view_page, 317907008),
# ]


# gevent.joinall(workers)

# for w in workers:
#     print w.value

