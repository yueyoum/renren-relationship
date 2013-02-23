# -*- coding: utf-8 -*-

import gevent.monkey
gevent.monkey.patch_all()

import gevent
from gevent import Timeout
from gevent.pool import Pool

import urllib
import urllib2
import cookielib
from functools import wraps

from lxml import etree


class TooLong(Exception):
    pass



def gtimeout(t):
    def deco(func):
        @wraps(func)
        def wrap(*args, **kwargs):
            try:
                with Timeout(t, TooLong):
                    return func(*args, **kwargs)
            except TooLong:
                print 'tool long, args=', args
                return []
        return wrap
    return deco




class RenRen(object):
    HEADERS = [
        ('User-Agent', 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:18.0) Gecko/20100101 Firefox/18.0'),
        ('Host', 'www.renren.com')
    ]

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.login()


    def login(self):
        url  = 'http://www.renren.com/ajaxLogin/login'
        data = urllib.urlencode({
                'email': self.email,
                'password': self.password,
                'origURL': 'http://www.renren.com/home',
                'domain': 'renren.com',
            })

        cookie = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
        self.opener.addheaders = self.HEADERS
        urllib2.install_opener(self.opener)

        request = urllib2.Request(url, data=data)
        res = urllib2.urlopen(request)


    def view_page(self, uid):
        url = 'http://www.renren.com/{0}/profile'.format(uid)
        res = self.opener.open(url)


    def get_friends(self, uid):
        URL = 'http://friend.renren.com/GetFriendList.do?curpage={0}&id=' + str(uid)
        first_page = self.opener.open(URL.format(0))

        parse = etree.HTMLParser()
        tree = etree.fromstring(first_page.read(), parse)
        friends_amount = int(tree.xpath('//div[@id="toc"]/p[1]/span/text()')[0])

        # print friends_amount

        friends_pages, _rest = divmod(friends_amount, 20)
        if _rest > 0:
            friends_pages += 1


        friends_xpath = '//div[@id="list-results"]//li/p/a/@href'
        all_friends = []


        first_page_friends = [f.split('=')[1] for f in tree.xpath(friends_xpath)]
        all_friends.extend(first_page_friends)


        @gtimeout(5)
        def _get(p):
            # print 'get page', p
            html = self.opener.open(URL.format(p))
            tree = etree.fromstring(html.read(), parse)
            res = [f.split('=')[1] for f in tree.xpath(friends_xpath)]
            return res

        # this is sync version
        # for i in range(1, friends_pages):
        #     all_friends.extend(_get(i))


        # this is async version
        pool = Pool(50)
        # at most spwan 50 greenlets, means get 1000 friends at one time
        for p in pool.imap_unordered(_get, xrange(1, friends_pages)):
            all_friends.extend(p)

        # workers = [gevent.spawn(_get, i) for i in range(1, friends_pages)]
        # gevent.joinall(workers)
        # for w in workers:
        #     all_friends.extend(w.value)


        # print all_friends
        # print len(all_friends), friends_amount
        return all_friends[:20]







with open('account', 'r') as f:
    data = f.readlines()
    email = data[0].rstrip('\n')
    password = data[1].rstrip('\n')


# r = RenRen(email, password)

# r.get_friends(256089759)
# r.get_friends(92094305)

# workers = [
#     gevent.spawn(r.view_page, 252572048),
#     gevent.spawn(r.view_page, 259057317),
#     gevent.spawn(r.view_page, 256089759),
#     gevent.spawn(r.view_page, 317907008),
# ]


# gevent.joinall(workers)

# for w in workers:
#     print w.value

class FriendsStore(object):
    def __init__(self, uid, level, parent=None):
        self.uid = uid
        self.level = level
        self.parent = parent
        self.friends = None

    def is_friend(self, target_uid):
        return target_uid in self.friends


class RenRenRelationShip(object):
    def __init__(self, email, password):
        self.renren = RenRen(email, password)
        self.slot = []

    def get_friend_obj_by_level(self, level):
        res = filter(lambda s: s.level == level, self.slot)
        print 'lv =', level, len(res)
        return res


    def collect_friends(self, uid, level=1):
        def _collect(fo):
            print 'collect ', fo.uid
            fo.friends = self.renren.get_friends(fo.uid)
            return fo


        fs = FriendsStore(uid, 0)
        self.slot.append(fs)

        pool = Pool(200)

        for l in range(level):
            pool_jobs = pool.imap_unordered(_collect, self.get_friend_obj_by_level(l))
            for fo in pool_jobs:
                self.slot.extend(
                        [FriendsStore(u, l+1, fo.uid) for u in fo.friends]
                    )



renren = RenRenRelationShip(email, password)
renren.collect_friends(92094305, 2)
print len(renren.slot)
