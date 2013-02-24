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

        print uid, friends_amount

        friends_pages, _rest = divmod(friends_amount, 20)
        if _rest > 0:
            friends_pages += 1


        friends_xpath = '//div[@id="list-results"]//li/p/a/@href'
        all_friends = []


        first_page_friends = [f.split('=')[1] for f in tree.xpath(friends_xpath)]
        all_friends.extend(first_page_friends)


        @gtimeout(5)
        def _get(p):
            # print 'get page', uid, p
            html = self.opener.open(URL.format(p))
            tree = etree.fromstring(html.read(), parse)
            res = [f.split('=')[1] for f in tree.xpath(friends_xpath)]
            return res

        # this is sync version
        # for i in range(1, friends_pages):
        #     all_friends.extend(_get(i))


        # this is async version
        pool = Pool(10)
        # at most spwan 50 greenlets, means get 1000 friends at one time
        for p in pool.imap_unordered(_get, xrange(1, friends_pages)):
            all_friends.extend(p)
            gevent.sleep(0)


        # print all_friends
        # print len(all_friends), friends_amount
        return all_friends[:30]
    







with open('account', 'r') as f:
    data = f.readlines()
    email = data[0].rstrip('\n')
    password = data[1].rstrip('\n')


# r = RenRen(email, password)

# r.get_friends(256089759)
# print r.get_friends(92094305)

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
    __slots__ = ('uid', 'level', 'parent', 'friends')

    def __init__(self, uid, level, parent=None):
        self.uid = uid
        self.level = level
        self.parent = parent
        self.friends = set()

    def has_friend(self, target_uid):
        return target_uid in self.friends
    
    def get_common_friends(self, friend_obj):
        return self.friends & friend_obj.friends


class RenRenRelationShip(object):
    def __init__(self, email, password):
        self.renren = RenRen(email, password)
        self.slot = []

    def get_friend_obj_by_level(self, level):
        return filter(lambda s: s.level == level, self.slot)


    def collect_friends(self, uid, level=1):
        @gtimeout(60)
        def _collect(fo):
            print 'collect ', fo.uid
            fo.friends = set(self.renren.get_friends(fo.uid))
            return fo


        fs = FriendsStore(uid, 0)
        self.slot.append(fs)

        #pool = Pool(100)
        #
        #for l in range(level):
        #    pool_jobs = pool.imap_unordered(_collect, self.get_friend_obj_by_level(l))
        #    for fo in pool_jobs:
        #        if fo:
        #            self.slot.extend(
        #                    [FriendsStore(u, l+1, fo.uid) for u in fo.friends]
        #                )
        #    gevent.sleep(0)
        
        for l in range(level):
            for fo in self.get_friend_obj_by_level(l):
                _collect(fo)
                self.slot.extend(
                    [FriendsStore(u, l+1, fo.uid) for u in fo.friends]
                )
                

        print 'collect done'
        self.slot.pop(0)



renren = RenRenRelationShip(email, password)
renren.collect_friends(92094305, 2)


import networkx as nx
import matplotlib.pyplot as plt

class GraphAnalysis(object):
    def __init__(self):
        self.G = nx.Graph()

    def import_data_from_friends_store(self, fs_list):
        for fs in fs_list:
            self.G.add_node(fs.uid, lv=fs.level)
            if fs.friends:
                edges = [(fs.uid, u) for u in fs.friends]
                self.G.add_edges_from(edges)


        for fs in fs_list:
            for _fs in fs_list:
                if fs == _fs:
                    continue

                if fs.has_friend(_fs.uid) and not self.G.has_edge(fs.uid, _fs.uid):
                    self.G.add_edge(fs.uid, _fs.uid)
                    


        # remove 
        nodes = self.G.nodes()
        for n in nodes:
            if self.G.degree(n) == 1:
                self.G.remove_node(n)


    def draw(self, it=50, f='x.png'):
        pos = nx.spring_layout(self.G, iterations=it)

        degree = nx.degree(self.G)
        
        def _size(d):
            if d > 10:
                d = 10
            return d * 10
                
        node_size = [_size(degree[n]) for n in self.G]

        nx.draw_networkx_nodes(self.G, pos, node_size=node_size)
        nx.draw_networkx_edges(self.G, pos, alpha=0.3)
        # nx.draw_networkx_labels(self.G, pos, alpha=0.6)

        plt.axis('off')
        plt.savefig(f, dpi=160)
        plt.clf()



g = GraphAnalysis()
g.import_data_from_friends_store(renren.slot)
# g.draw()


