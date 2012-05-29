#!/usr/bin/python
# -*- coding: utf-8 -*-
################################################################################

import functools
import math
import pymongo
import sys
from itertools import islice
from os.path import basename

def memoize(db, collection):
    connection = pymongo.Connection('localhost', 1979)
    db_ = connection[db]
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                db_[collection].ensure_index(
                    [(k, pymongo.ASCENDING) for k in kwargs.keys()]
                    )
                result = db_[collection].find_one(kwargs)
                if result:
                    #print >>sys.stderr, 'MONGODB: HIT in %s.%s: %s' % \
                    #    (db, collection, result)
                    return result['value']
                else:
                    #print >>sys.stderr, 'MONGODB: MISS in %s.%s: %s' % \
                    #    (db, collection, kwargs)
                    value = func(*args, **kwargs) 
                    if value:
                        result = kwargs
                        result['value'] = value
                        #print >>sys.stderr, 'MONGODB: CACHING in %s.%s: %s:' % \
                        #    (db, collection, result)
                        db_[collection].insert(result)
                        return value
            except Exception as err:
                #print >>sys.stderr, 'MONGODB MEMOIZATION ERROR!', err, args, kwargs
                #raise err
                f = func(*args, **kwargs)
                #print >>sys.stderr, '%s(%s, %s): %s' % (func, args, kwargs, f)
                return f
        return wrapper
    return decorator

def dbname(db_):
    '''return host, port, database, and collection name of db'''
    host = db_._Collection__database._Database__connection.host
    port = db_._Collection__database._Database__connection.port
    database = db_._Collection__database._Database__name
    collection = db_.name
    return '%s:%d/%s.%s' % (host, port, database, collection)

def file2collection(file):
    '''sanitize a filename to use as a collection'''
    return basename(file).split('.')[0].split('-')[0]

def staggered_retrieval(iterator, maximum, batch):
    '''returns items in iterator by iterating over slices of size N'''
    slices = int(math.ceil(float(maximum) / batch))
    print >>sys.stdout, 'slices:', slices
    return (x
            for x in islice(iterator, batch)
            for y in xrange(slices))

def fast_find(db, c, query={}, batch=1000, **kwargs):
    with db[c].find(spec=query, batch=batch, timeout=False, **kwargs) as xs:
        # print >>sys.stderr, '%s.find(spec=%s,batch=%s,kwargs=%s).explain(): %s' % (db[c], query, batch, kwargs, xs.explain())
        slices = int(math.ceil(float(xs.count()) / batch))
        for y in xrange(slices):
            for x in islice(xs, batch):
                yield x