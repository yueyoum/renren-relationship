# -*- coding: utf-8 -*-

import functools

import gevent



class TooLong(Exception):
    pass



def retry(times=2):
    def deco(func):
        @functools.wraps(func)
        def wraps(*args, **kwargs):
            for t in range(times):
                try:
                    return func(*args, **kwargs)
                except TooLong:
                    gevent.sleep(1)
                    continue
            print 'try %d times, but still failure' % times
            return []
        return wraps
    return deco



def gtimeout(t=10, mute=False):
    def deco(func):
        @functools.wraps(func)
        def wrap(*args, **kwargs):
            try:
                with gevent.Timeout(t, TooLong):
                    return func(*args, **kwargs)
            except TooLong:
                print 'too long, args =', args
                if mute:
                    return []
                raise
        return wrap
    return deco


