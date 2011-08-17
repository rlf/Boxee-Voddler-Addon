# voddlerapi.py - methods for accessing the voddlerapi
import urllib2

def getURL(url, postData=None):
    f = urllib2.urlopen(url, postData)
    data = f.read()
    print "%s?%s\n%s" % (url, postData, data)
    return data
