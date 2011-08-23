# voddlerapi.py - methods for accessing the voddlerapi
import urllib2, urllib, login
try: import json
except: import simplejson as json
import re
import string
from status import *
from pprint import pprint

BASE_URL = "http://api.voddler.com/"
META_API = BASE_URL + "metaapi/"
USER_API = BASE_URL + "userapi/"

# META API
SEARCH_URL = META_API + "browse/1?%s"
GENRE_URL = META_API + "genres/1?%s"
INFO_URL = META_API + "info/1?%s"

# USER API
LOGIN_URL = USER_API + "login/1"
TOKEN_URL = USER_API + "vnettoken/1"
PLAYLIST_URL = USER_API + "playlists/1"
PLAYLIST_ADD_URL = USER_API + "playlistadd/1"
PLAYLIST_REMOVE_URL = USER_API + "playlistremove/1"

# PLAYER URLs
PLAYER1_URL = "https://www.voddler.com/playapi/embedded/1?session=%s&videoId=%s&format=html"
FLASH_PLAYER_URL_QUOTED = urllib.quote_plus('http://player.voddler.com/VoddlerPlayer.swf')
PLAYER2_URL = "flash://player.voddler.com/src=%s&bx-cookie=%s"

PLATFORMS = ['iphone', 'web', 'android', 'symbian']

# why Voddler uses movies and movie randomly... beats me
genreFilter = {'movie' : 'movies', 'episode' : 'episodes'}

# syntax (pattern, indices), indices = (title, season, episode, subtitle), 0 means not available
episodePatterns = [(re.compile('(.*) - (.*) s([0-9]*)[ ]?e[p]?([0-9]*)', re.I | re.U), (1, 3, 4, 2)),\
                   (re.compile('(.*) s([0-9]*)[ ]?e[p]?([0-9]*)(.*)', re.I | re.U), (1, 2, 3, 0)),\
                   (re.compile('(.*) series ([0-9]*) e[p]?([0-9]*)(.*)', re.I | re.U), (1, 2, 3, 4)), \
                   (re.compile('(.*) ( - .*)([0-9]*)x([0-9]*)', re.I | re.U), (1, 3, 4, 2)), \
                   (re.compile('(.*) ([0-9]*)x([0-9]*)', re.I | re.U), (1, 2, 3, 0)), \
                   (re.compile('(.*) e[p]?([0-9]*)(.*)', re.I | re.U), (1, 0, 2, 0)), \
                   (re.compile('(.*) - (.*)', re.I | re.U), (1, 0, 0, 2))]

''' Convenience function for converting unicode to a str
'''
def u2s(u):
    return u.encode('utf-8', 'xmlcharrefreplace')

def u2a(u):
    return u.encode('ascii')

def sortAlpha(x,y):
    return cmp(x.getTitle(), y.getTitle())

def sortRating(x,y):
    c = cmp(y.getRating(), x.getRating()) # higher comes first
    if c == 0:
        return sortAlpha(x,y)
    return c

sortMethods = {'rating' : sortRating, 'alphabetical' : sortAlpha, 'views' : sortRating}

def _getURL(url, postData=None):
    if postData:
        print "%s?%s" % (url, postData)
    else:
        print "%s" % (url)
    if url.find("%") is not -1:
        f = urllib2.urlopen(url % postData) # GET
    else:
        f = urllib2.urlopen(url, postData) # POST
    data = f.read()
    print data
    return data

''' Tries to deduce information about the episode be using info from the movie
'''
def _getTitleInfo(movie):
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
        print "Could not find a pattern for '%s'" % u2s(title)
    # TODO: actually look this up, once we get somewhere
    return seriesTitle, season, episode, subtitle

''' Filters data - i.e. reorganizes tvseries into something more like movies...
'''
def _postProcess(data, series={}):
    for movie in data[u'data'][u'videos']:
        title, season, episode, subtitle = _getTitleInfo(movie)
        if title not in series.keys():
            series[title] = movie
            movie[u'originalTitle'] = title
            movie[u'localizedData'][u'synopsis'] = u'' # Unfortunately we don't have synopsis for the whole series
            # TODO: remove the more episode specific data from the "movie"
            series[title]['seasons'] = { season : {}}
        if season not in series[title]['seasons'].keys():
            series[title]['seasons'][season] = {}
        series[title]['seasons'][season][episode] = { 'title' : title + subtitle, 'synopsis' : movie[u'localizedData'][u'synopsis'] }
        series[title][u'localizedData'][u'synopsis'] += season + episode + u' '
    data[u'data'][u'videos'] = series.values()
    return data

api = None
def getAPI():
    global api
    if not api:
        api = VoddlerAPI()
    return api

class VoddlerAPI:
    def __init__(self):
        self.sessionId = None
        self.token = None
        self.movieCache = {}
        self.genreCache = {'all' : {}}
        self.playlists = {}

    ''' Return a dict of key : value for this type of movie
    '''
    def getGenres(self, type='movie'):
        if type in self.genreCache.keys():
            return self.genreCache[type]
        gtype = type
        if type in genreFilter.keys():
            gtype = genreFilter[type]
        jsonData = _getURL(GENRE_URL, urllib.urlencode({'type' : gtype}))
        data = json.loads(jsonData)
        pprint(data)
        dict = {}
        for g in data[u'data']:
            k = u2s(g[u'value'])
            v = u2s(g[u'name'])
            dict[k] = v
            self.genreCache['all'][k] = v
        self.genreCache[type] = dict
        return dict

    ''' Return a list of Movie objects
    '''
    def search(self, type='movie', category='free', genre='all', sort='rating', offset=0, count=100):
        if type not in self.genreCache.keys():
            # we don't store them, we just need the cache to be updated
            self.getGenres(type)
        if not self.playlists:
            self.getPlaylists() # fetch em
        dict = {'type' : type, 'category' : category, 'genre' : genre, 'sort' : sort, 'offset' : offset, 'count' : count}
        jsonData = _getURL(SEARCH_URL, urllib.urlencode(dict))
        data = json.loads(jsonData)
        max = data[u'data'][u'count']
        if type == 'episode':
            # TODO: Is this too heavy?
            series = {}
            data = _postProcess(data, series)
            while ((offset+count) < max) and (genre != 'all'):
                num = (offset / count) + 1
                status("Fetching episodes", num, math.ceil(max/count))
                offset += count
                jsonData = _getURL(SEARCH_URL % urllib.urlencode(dict)) # only GET supported
                d = json.loads(jsonData)
                _postProcess(d, series)
            status("Sorting TVSeries")
            data[u'data'][u'videos'] = series.values()
            data[u'data'][u'count'] = len(series)
            if genre != 'all':
                max = len(series)
        # 'all' because some vids are in more than one category... sigh...
        vids = [Movie(vid, self.genreCache['all'], self.playlists) for vid in data[u'data'][u'videos']]
        if type == 'episode':
            vids.sort(sortMethods[sort])
        return max, vids

    def getSessionId(self):
        return self.sessionId

    ''' Returns a sessionid and enables the VodderAPI to use functionality that requires login.
    '''
    def login(self, username, password):
        jsonData = _getURL(LOGIN_URL, urllib.urlencode({'username' : username, 'password' : password}))
        data = json.loads(jsonData)
        if data[u'success']:
            self.sessionId = data[u'data'][u'session'].encode('ascii')
        return self.sessionId

    def getInfo(self, videoId):
        jsonData = _getURL(INFO_URL, urllib.urlencode({'videoId' : videoId}))
        data = json.loads(jsonData)
        return Movie(data[u'data'][u'videos'])

    def getToken(self):
        if not self.sessionId:
            raise "You must be logged in before asking for a token"
        if self.token:
            return self.token
        jsonData = _getURL(TOKEN_URL, urllib.urlencode({'session' : self.sessionId}))
        data = json.loads(jsonData)
        if data[u'success']:
            self.token = u2s(data[u'data'][u'token'])
        return self.token

    ''' Returns a dictionary with key : [video-ids] of the different playlists.
    '''
    def getPlaylists(self):
        if not self.sessionId:
            raise "You need to be logged in to retrieve playlists"
        if self.playlists:
            return self.playlists
        jsonData = _getURL(PLAYLIST_URL, urllib.urlencode({'session' : self.sessionId}))
        data = json.loads(jsonData)
        playlists = {}
        for playlist in data[u'data'][u'playlists']:
            type = playlist[u'type']
            videos = []
            for video in playlist[u'videos']:
                videos.append(video[u'id'])
            playlists[type] = {}
            playlists[type]['videos'] = videos
            playlists[type]['id'] = u2s(playlist[u'id'])
        self.playlists = playlists
        return playlists

    def getMoviesOnPlaylist(self, type, sort='rating'):
        list = self.getPlaylists()
        if type == 'history':
            sort = None # History is ALWAYS database order
        movies = self.getVideosForPlaylist(list[type]['videos'], sort)
        return len(movies), movies

    def addToPlaylist(self, videoId, list='favorites'):
        if not self.playlists:
            self.getPlaylists() # just to make sure we initialize self.playlists
        if not self.sessionId:
            raise "You need to be logged in to manage playlists"
        jsonData = _getURL(PLAYLIST_ADD_URL, urllib.urlencode({'playlist' : self.playlists[list]['id'], 'video' : videoId, 'session' : self.sessionId}))
        data = json.loads(jsonData)
        if data[u'success']:
            self.playlists[list]['videos'].append(videoId)
        else:
            raise "Unable to add to playlist : %s" % data[u'message']

    def removeFromPlaylist(self, videoId, list='favorites'):
        if not self.playlists:
            self.getPlaylists() # just to make sure we initialize self.playlists
        if not self.sessionId:
            raise "You need to be logged in to manage playlists"
        jsonData = _getURL(PLAYLIST_REMOVE_URL, urllib.urlencode({'playlist' : self.playlists[list]['id'], 'video' : videoId, 'session' : self.sessionId}))
        data = json.loads(jsonData)
        if data[u'success']:
            self.playlists[list]['videos'].remove(videoId)
        else:
            raise "Unable to remove from playlist : %s" % data[u'message']

    def getVideoInfo(self, videoId):
        jsonData = _getURL(INFO_URL, urllib.urlencode({'videoId' : videoId}))
        data = json.loads(jsonData)
        type = 'movie' # may not be correct!
        if not type in self.genreCache.keys():
            self.getGenres(type)
        return Movie(data[u'data'][u'videos'], self.genreCache[type], self.playlists)

    def getVideosForPlaylist(self, ids, sort='rating'):
        videos = []
        for id in ids:
            videos.append(self.getVideoInfo(id))
        if sort:
            videos.sort(sortMethods[sort])
        return videos

    def getMovieURL(self, videoId, player='flash'):
        if player=='embed':
            if not self.sessionId:
                raise "You have to be logged in to play movies"
            return PLAYER1_URL % (self.sessionId, videoId)
        elif player=='flash':
            # generate a flash url
            dict = {'videoid' : videoId, 'cridid' : 1, 'token' : self.getToken()}
            cookie = urllib.quote_plus(urllib.urlencode(dict))
            return PLAYER2_URL % (FLASH_PLAYER_URL_QUOTED, cookie)
        return None

class Movie:
    def __init__(self, data, genreDict, playlists):
        self.data = data
        self.genreDict = genreDict
        self.playlists = playlists

    def getId(self):
        return self._getData(u'id')

    def getTitle(self):
        return self._getData(u'originalTitle')

    def getDescription(self):
        return self._getData(u'localizedData/synopsis')

    def getIcon(self):
        return self._getData(u'posterUrl')

    def getURL(self):
        return self._getData(u'url')

    def _getType(self):
        return self.getData(u'type')

    def getGenres(self):
        genres = []
        for key in self._getList(u'genres'):
            k = u2s(key)
            if k in self.genreDict:
                genres.append(self.genreDict[k])
            else:
                # Apparently Voddler mixes genres - even though the API doesn't include them.
                print "Genre: %s was not found for this type of movies" % k
                genres.append(string.capitalize(k))
        return string.join(genres, ', ')

    def getDurationSeconds(self):
        return int(self._getData(u'runtime')) * 60

    def getDurationFormatted(self):
        secs = self.getDurationSeconds()
        minutes = secs / 60
        hour = minutes / 60
        minutes = minutes % 60
        if hour:
            return "%ih %imin" % (hour, minutes)
        else:
            return "%imin" % (minutes)

    def getRating(self):
        return self._getData(u'videoRatingAverage')

    def getYear(self):
        return self._getData(u'productionYear')

    def getDetails(self):
        return "%s | %s" % (self.getYear(), self.getDurationFormatted())

    def getCast(self):
        castList = []
        for cast in self._getList(u'castMembers'):
            castList.append(CastAndRole(cast[u'name'], cast[u'role']))
        return castList

    def getPlatforms(self):
        platforms = []
        for platform in self._getList(u'platforms'):
            platforms.append(u2s(platform))
        return platforms

    def getTrailers(self):
        trailers = []
        url = self._getData(u'trailer')
        if url:
            trailers.append(Trailer(url, 'Trailer HD'))
        url = self._getData(u'trailerLowRes')
        if url:
            trailers.append(Trailer(url, 'Trailer SD'))
        return trailers

    def getScreenshots(self):
        shots = []
        # TODO: the structure actually supports ordering...
        for shot in self._getList(u'screenshots'):
            shots.append(u2a(shot[u'url']))
        return shots

    def showOnListItem(self, item, index=0):
        item.SetDuration(self.getDurationSeconds())
        item.SetLabel(self.getTitle())
        id = self.getId()
        item.SetProperty('id', id)
        item.SetProperty('genres', self.getGenres())
        item.SetProperty("details", self.getDetails())
        item.SetDescription(self.getDescription(), True)
        iconUrl = self.getIcon()
        item.SetThumbnail(iconUrl)
        item.SetIcon(iconUrl)
        url = self.getURL()
        item.SetPath(url)
        item.SetProperty('url', url)
        item.SetContentType('text/html')
        rating = self.getRating()
        item.SetStarRating(rating)
        item.SetProperty('rating', "%02i" % (math.floor(rating * 20) / 2))
        castList = []
        for cast in self.getCast():
            item.AddCastAndRole(cast.getName(), cast.getRole())
            castList.append(cast.getName())

        item.SetProperty('cast', string.join(castList, ', '))
        for platform in PLATFORMS:
            item.SetProperty('on_%s' % platform, 'false')
        for platform in self.getPlatforms():
            item.SetProperty('on_%s' % platform, 'true')

        for trailer in self.getTrailers():
            item.AddAlternativePath(trailer.getName(), trailer.getURL(), 'video/mp4', iconUrl)
            item.SetProperty(trailer.getName(), trailer.getURL())
            item.SetProperty('hasTrailer', 'true')

        cnt = 0
        for url in self.getScreenshots():
            item.SetImage(cnt, url)
            item.SetProperty('image%i' % cnt, url)
            cnt += 1
        item.SetProperty('ix', "%i" % (index+1))

        playlists = ['favorites', 'playlist']
        for list in playlists:
            if id in self.playlists[list]['videos']:
                item.SetProperty("is%s" % string.capitalize(list), 'true')
            else:
                item.SetProperty("is%s" % string.capitalize(list), 'false')

    def _getData(self, ukey, dict=None):
        if dict is None:
            dict = self.data
        ix = ukey.find(u'/')
        if ix is not -1:
            prekey = ukey[:ix]
            postkey = ukey[ix+1:]
            return self._getData(postkey, dict[prekey])
        if type(dict[ukey]) == unicode:
            return dict[ukey].encode('utf-8', 'xmlcharrefreplace')
        return dict[ukey]

    def _getList(self, ukey, dict=None):
        if dict is None:
            dict = self.data
        ix = ukey.find(u'/')
        if ix is not -1:
            prekey = ukey[:ix]
            postkey = ukey[ix+1:]
            return self._getList(postkey, dict[prekey])
        return self.data[ukey]

class Trailer:
    def __init__(self, url, name):
        self.url = url
        self.name = name
    def getName(self):
        return self.name
    def getURL(self):
        return self.url

class CastAndRole:
    def __init__(self, name, role):
        self.name = name.encode('utf-8', 'xmlcharrefreplace')
        self.role = role.encode('utf-8', 'xmlcharrefreplace')

    def getName(self):
        return self.name

    def getRole(self):
        return self.role
