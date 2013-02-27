# -*- coding: utf-8 -*-

import gevent.monkey
gevent.monkey.patch_all()

from gevent.pool import Pool


import random
import urllib
import urllib2
import cookielib

from lxml import etree



from utils import retry, gtimeout



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




class RenRen(object):
    USER_AGENT = [
        'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.57 Safari/537.17',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Ubuntu Chromium/23.0.1271.97 Chrome/23.0.1271.97 Safari/537.11',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.56 Safari/537.17',
        'Mozilla/5.0 (X11; Linux i686) AppleWebKit/534.34 (KHTML, like Gecko) rekonq/1.1 Safari/534.34',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/536.26.17 (KHTML, like Gecko) Version/6.0.2 Safari/536.26.17',
    ]
    
    
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.login()
    
    
    @classmethod
    def random_user_agent(cls):
        return random.choice(cls.USER_AGENT)
    
    
    @property
    def headers(self):
        return [
            ('User-Agent', RenRen.random_user_agent()),
        ]
    

    def login(self):
        url  = 'http://www.renren.com/ajaxLogin/login'
        data = urllib.urlencode({
                'email': self.email,
                'password': self.password,
                'origURL': 'http://www.renren.com/home',
                'domain': 'renren.com',
            })

        self.cookie = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookie))
        #self.opener.addheaders = self.headers
        
        # 不知为何，这里不能带 headers，没有headers反而顺利请求
        self.opener.addheaders = []
        urllib2.install_opener(self.opener)

        request = urllib2.Request(url, data=data)
        urllib2.urlopen(request)
        print self.email, 'login done'


    def view_page(self, uid):
        url = 'http://www.renren.com/{0}/profile'.format(uid)
        self.opener.open(url)


    def get_friends(self, uid):
        URL = 'http://friend.renren.com/GetFriendList.do?curpage={0}&id=' + str(uid)
        first_page = self.opener.open(URL.format(0))

        parse = etree.HTMLParser()
        tree = etree.parse(first_page, parse)
        friends_amount = int(tree.xpath('//div[@id="toc"]/p[1]/span/text()')[0])

        print uid, friends_amount

        friends_pages, _rest = divmod(friends_amount, 20)
        if _rest > 0:
            friends_pages += 1


        friends_xpath = '//div[@id="list-results"]//li/p/a/@href'
        all_friends = []


        first_page_friends = [f.split('=')[1] for f in tree.xpath(friends_xpath)]
        all_friends.extend(first_page_friends)


        @retry()
        @gtimeout()
        def _get(p):
            print '_get', uid, p
            html = self.opener.open(URL.format(p))
            tree = etree.parse(html, parse)
            res = [f.split('=')[1] for f in tree.xpath(friends_xpath)]
            return res

        #this is sync version
        for i in range(1, friends_pages):
            all_friends.extend(_get(i))


        # 多次测试发现，对同一个人的好友不能并发请求，
        # 如果并发，这些请求全部会block住，没有响应。
        # 所以是对不同的人起多个并发请求

        ## this is gevent version
        #pool = Pool(2)
        #for p in pool.imap_unordered(_get, xrange(1, friends_pages)):
        #    all_friends.extend(p)
        #    gevent.sleep(0)


        return all_friends[:100]
    



class RenRenRelationShip(object):
    def __init__(self, accounts):
        self.renrens = [RenRen(email, password) for email, password in accounts]
        self.slot = []
        
    
    @property
    def renren(self):
        return random.choice(self.renrens)


    def get_friend_obj_by_level(self, level):
        return filter(lambda s: s.level == level, self.slot)


    def collect_friends(self, uid, level=1):
        @gtimeout(90, mute=True)
        def _collect(fo):
            print 'collect ', fo.uid
            fo.friends = set(self.renren.get_friends(fo.uid))
            return fo


        fs = FriendsStore(uid, 0)
        self.slot.append(fs)

        pool = Pool(20)
        for l in range(level):
            pool_jobs = pool.imap_unordered(_collect, self.get_friend_obj_by_level(l))
            for fo in pool_jobs:
                if fo:
                    self.slot.extend(
                            [FriendsStore(u, l+1, fo.uid) for u in fo.friends]
                        )
        
        #for l in range(level):
        #    for fo in self.get_friend_obj_by_level(l):
        #        _collect(fo)
        #        if fo:
        #            self.slot.extend(
        #                [FriendsStore(u, l+1, fo.uid) for u in fo.friends]
        #            )
                
        print 'collect done'
        self.slot.pop(0)





with open('account', 'r') as f:
    data = f.readlines()
    data = [d.rstrip('\n') for d in data]
    accounts = zip(data[::2], data[1::2])
    


r = RenRenRelationShip(accounts)
r.collect_friends(92094305, 2)


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
            if d > 50:
                d = 50
            return d
                
        node_size = [_size(degree[n]) for n in self.G]

        nx.draw_networkx_nodes(self.G, pos, node_size=node_size)
        nx.draw_networkx_edges(self.G, pos, alpha=0.3)
        # nx.draw_networkx_labels(self.G, pos, alpha=0.6)

        plt.axis('off')
        plt.savefig(f, dpi=200)
        plt.clf()



g = GraphAnalysis()
g.import_data_from_friends_store(r.slot)
# g.draw()


