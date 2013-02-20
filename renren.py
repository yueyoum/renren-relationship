# -*- coding: utf-8 -*-

import urllib
import urllib2
import cookielib


class RenRen(object):
    HEADERS = {
        'Host': 'www.renren.com',
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:18.0) Gecko/20100101 Firefox/18.0',
        'Referer': 'http://www.renren.com/SysHome.do',
    }

    LOGIN_URL = 'http://www.renren.com/ajaxLogin/login'

    def __init__(self, email, password):
        self.email = email
        self.password = password


    def login(self):
        # data 从 firebug 抓包获取
        data = {
            'email': self.email,
            'password': self.password,
            #'origURL': 'http://www.renren.com/home',
            #'domain': 'renren.com',
            #'key_id': 1,
            #'captcha_type': 'web_login',
        }

        data = urllib.urlencode(data)

        cookie = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie))
        urllib2.install_opener(self.opener)

        request = urllib2.Request(self.LOGIN_URL, data=data, headers=self.HEADERS)
        res = urllib2.urlopen(request)

        #res = self.opener.open(self.LOGIN_URL, data)
        return res.read()

    def view_page(self, uid):
        url = 'http://www.renren.com/{0}/profile'.format(uid)
        #res = self.opener.open(url)
        res = urllib2.urlopen(url)
        return res.read()


with open('account', 'r') as f:
    data = f.readlines()
    email = data[0].rstrip('\n')
    password = data[1].rstrip('\n')

print email
print password
r = RenRen(email, password)
print r.login()

print r.view_page(179945202)

