# voddlerapi.py - methods for accessing the voddlerapi
import mc
import urllib2, urllib, login
try: import json
except: import simplejson as json
import login as loginapi

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
genreFilter = {'movie' : 'movies'}

def getURL(url, postData=None):
    f = urllib2.urlopen(url, postData)
    data = f.read()
    print "%s?%s\n%s" % (url, postData, data)
    return data

def getGenres(type='movie'):
    if type in genreFilter.keys():
        type = genreFilter[type]
    dict = {'type' : type}
    jsonData = getURL(GENRE_URL % urllib.urlencode(dict)) # only GET supported
    data = json.loads(jsonData)
    return data

def searchVoddler(type='movie', category='free', genre='all', sort='rating', offset=0, count=100):
    dict = {'type' : type, 'category' : category, 'genre' : genre, 'sort' : sort, 'offset' : offset, 'count' : count}
    jsonData = getURL(SEARCH_URL % urllib.urlencode(dict)) # only GET supported
    data = json.loads(jsonData)
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
