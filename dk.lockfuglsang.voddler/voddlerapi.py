# voddlerapi.py - methods for accessing the voddlerapi
import mc
import urllib2, urllib, login
try: import json
except: import simplejson as json
import login as loginapi
import re

BASE_URL = "http://api.voddler.com/"
META_API = BASE_URL + "metaapi/"
USER_API = BASE_URL + "userapi/"

SEARCH_URL = META_API + "browse/1?%s"
GENRE_URL = META_API + "genres/1?%s"

LOGIN_URL = USER_API + "login/1"
TOKEN_URL = USER_API + "vnettoken/1"
PLAYER1_URL = "https://www.voddler.com/playapi/embedded/1?session=%s&videoId=%s&format=html"
FLASH_PLAYER_URL_QUOTED = urllib.quote_plus('http://player.voddler.com/VoddlerPlayer.swf')
PLAYER2_URL = "flash://player.voddler.com/src=%s&bx-cookie=%s"

# why Voddler uses movies and movie randomly... beats me
genreFilter = {'movie' : 'movies', 'episode' : 'episodes'}

# syntax (pattern, indices), indices = (title, season, episode, subtitle)
episodePatterns = [(re.compile('(.*) - (.*) s([0-9]*)[ ]?e[p]?([0-9]*)', re.I | re.U), (1, 3, 4, 2)),\
                   (re.compile('(.*) s([0-9]*)[ ]?e[p]?([0-9]*)(.*)', re.I | re.U), (1, 2, 3, 0)),\
                   (re.compile('(.*) series ([0-9]*) e[p]?([0-9]*)(.*)', re.I | re.U), (1, 2, 3, 4)), \
                   (re.compile('(.*) ( - .*)([0-9]*)x([0-9]*)', re.I | re.U), (1, 3, 4, 2)), \
                   (re.compile('(.*) ([0-9]*)x([0-9]*)', re.I | re.U), (1, 2, 3, 0)), \
                   (re.compile('(.*) e[p]?([0-9]*)(.*)', re.I | re.U), (1, 0, 2, 0))]

def sortAlpha(x,y):
    return cmp(x[u'originalTitle'], y[u'originalTitle'])

def sortRating(x,y):
    c = cmp(x[u'videoRatingAverage'], y[u'videoRatingAverage'])
    if c == 0:
        return sortAlpha(x,y)
    return c

sortMethods = {'rating' : sortRating, 'alphabetical' : sortAlpha, 'views' : sortRating}

def getURL(url, postData=None):
    if postData:
        print "%s?%s" % (url, postData)
    else:
        print "%s" % (url)
    f = urllib2.urlopen(url, postData)
    data = f.read()
    print data
    return data

def getGenres(type='movie'):
    if type in genreFilter.keys():
        type = genreFilter[type]
    dict = {'type' : type}
    jsonData = getURL(GENRE_URL % urllib.urlencode(dict)) # only GET supported
    data = json.loads(jsonData)
    if type == 'episodes':
        # remove All from the option...
        data[u'data'] = data[u'data'][1:]
    return data

def searchVoddler(type='movie', category='free', genre='all', sort='rating', offset=0, count=100):
    if type == 'episode':
        count = 200
    dict = {'type' : type, 'category' : category, 'genre' : genre, 'sort' : sort, 'offset' : offset, 'count' : count}
    jsonData = getURL(SEARCH_URL % urllib.urlencode(dict)) # only GET supported
    data = json.loads(jsonData)
    if type == 'episode':
        series = {}
        data = _postProcess(data, series)
        while offset+count < data[u'data'][u'count']:
            offset += count
            jsonData = getURL(SEARCH_URL % urllib.urlencode(dict)) # only GET supported
            d = json.loads(jsonData)
            _postProcess(d, series)
        data[u'data'][u'videos'] = series.values()
        data[u'data'][u'count'] = len(series)
        data[u'data'][u'videos'].sort(sortMethods[sort])
    return data

def login(username, password):
    jsonData = getURL(LOGIN_URL, urllib.urlencode({'username' : username, 'password' : password}))
    data = json.loads(jsonData)
    return data

def getToken(sessionId):
    jsonData = getURL(TOKEN_URL, urllib.urlencode({'session' : sessionId}))
    data = json.loads(jsonData)
    return data

def getPlayerURL(videoId):
    config = mc.GetApp().GetLocalConfig()
    player = config.GetValue('player')
    if player=='embed':
        sId = loginapi.getSessionId()
        if sId:
            return PLAYER1_URL % (sId, videoId)
    elif player=='flash':
        token = loginapi.getTokenId()
        if token:
            # generate a flash url
            dict = {'videoid' : videoId, 'cridid' : 1, 'token' : token}
            cookie = urllib.quote_plus(urllib.urlencode(dict))
            return PLAYER2_URL % (FLASH_PLAYER_URL_QUOTED, cookie)
    return None

''' Tries to deduce information about the episode be using info from the movie
'''
def getTitleInfo(movie):
    global episodePatterns
    title = movie[u'originalTitle']
    seriesTitle = title
    season = u'S01'
    episode = u'E01'
    subtitle = title
    for p in episodePatterns:
        m = p[0].match(title)
        if m:
            if p[1][0]:
                seriesTitle = m.group(p[1][0])
            if p[1][1]:
                season = u'S' + m.group(p[1][1])
            if p[1][2]:
                episode = u'E' + m.group(p[1][2])
            if p[1][3]:
                subtitle = m.group(p[1][3])
            break
    if seriesTitle == title:
        print "Could not find a pattern for '%s'" % title.encode('utf-8', 'xmlcharreplace')
    # TODO: actually look this up, once we get somewhere
    return seriesTitle, season, episode, subtitle

''' Filters data - i.e. reorganizes tvseries into something more like movies...
'''
def _postProcess(data, series={}):
    for movie in data[u'data'][u'videos']:
        title, season, episode, subtitle = getTitleInfo(movie)
        if title not in series.keys():
            series[title] = movie
            movie[u'originalTitle'] = title
            # TODO: remove the more episode specific data from the "movie"
            series[title]['seasons'] = { season : {}}
        if season not in series[title]['seasons'].keys():
            series[title]['seasons'][season] = {}
        series[title]['seasons'][season][episode] = { 'title' : title + subtitle, 'synopsis' : movie[u'localizedData'][u'synopsis'] }
    data[u'data'][u'videos'] = series.values()
    return data

