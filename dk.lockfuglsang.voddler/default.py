# Main .py file

import string, math
import mc
from mc import *
import urllib2
try: import json
except: import simplejson as json
from pprint import pprint

WINDOW_ID=14000
STATUS_ID=100
PROGRESS_ID=600
BASE_URL = "http://api.voddler.com/metaapi/"
LOGIN_URL = "https://api.voddler.com/userapi/login/1?username=%s&password=%s"
TOKEN_URL = "https://api.voddler.com/userapi/vnettoken/1?session=%s"
PLAYER1_URL = "https://www.voddler.com/playapi/embedded/1?session=%s&videoId=%s&format=html"
PLAYER2_URL = "http://player.voddler.com/VoddlerPlayer.swf?vnettoken=%s&videoId=%s"
PLAYER=1
PAGE_SIZE=100
sessionId = "5aba3b1cf4f03e0cba8971d3fd695fbd"
# -----------------------------------------------------------------------------
# Actions
# -----------------------------------------------------------------------------
def selectMovie():
    movieList = GetActiveWindow().GetList(200)
    index = movieList.GetFocusedItem()
    movie = movieList.GetItem(index)
    # change Path to point to the relevant movieUrl
    ShowDialogWait()
    status("Playing movie %s" % movie.GetLabel())
    try:
        url = getMovieURL(movie.GetProperty('id'))
        if url:
            print "- url %s" % url
            movie.SetPath(url)
            hideWaitDialog()
            GetPlayer().PlayWithActionMenu(movie)
        else:
            print "error playing movie"
    finally:
        hideWaitDialog()

def search():
    ShowDialogWait()
    saveUserSettings()
    try:
        movies = GetActiveWindow().GetList(200)
        items = ListItems()
        movies.SetItems(items)

        g = getGenre()
        s = getSorting()
        c = getCategory()
        status("Fetching movies...")
        jsonData = getURL(BASE_URL + "browse/1?type=movie&category=%s&genre=%s&sort=%s&offset=0&count=%s" % (c, g, s, PAGE_SIZE));
        data = json.loads(jsonData)
        items = ListItems()
        max_cnt = min(int(data[u'data'][u'count']), PAGE_SIZE)
        item_cnt = 1
        for movie in data[u'data'][u'videos']:
            status("Parsing movies %i of %i" % (item_cnt, max_cnt), item_cnt, max_cnt)
            title = movie[u'originalTitle'].encode('utf-8', 'xmlcharrefreplace')
            description = movie[u'localizedData'][u'synopsis'].encode('utf-8', 'xmlcharrefreplace')
            iconUrl = movie[u'posterUrl'].encode('ascii', 'xmlcharrefreplace')
            screenShots = movie[u'screenshots']
            movieUrl = movie[u'url'].encode('ascii', 'error')
            duration = movie[u'runtime'] * 60
            durationHour = movie[u'runtime'] / 60
            durationMinute = movie[u'runtime'] % 60
            durationFormatted = "%ih %imin" % (durationHour, durationMinute)
            if durationHour == 0:
                durationFormatted = "%imin" % durationMinute

            rating = movie[u'videoRatingAverage']
            releaseYear = movie[u'productionYear']
            if not releaseYear:
                releaseYear = '-'

            print "==============================================================="
            pprint(movie)
            item = ListItem(ListItem.MEDIA_VIDEO_FEATURE_FILM)
            item.SetDuration(duration)
            item.SetLabel(title)
            item.SetProperty('id', movie[u'id'].encode('ascii'))
            item.SetProperty('genres', getGenres(movie[u'genres']))
            item.SetProperty("details", "%s | %s" % (releaseYear, durationFormatted))
            item.SetDescription(description, True)
            item.SetThumbnail(iconUrl)
            item.SetIcon(iconUrl)
            item.SetProperty('poster', iconUrl)
            item.SetPath(movieUrl)
            item.SetContentType('text/html')
            item.SetStarRating(rating)
            item.SetProperty('rating', "%02i" % (math.floor(rating*20)/2))

            castList = []
            for cast in movie[u'castMembers']:
                role = cast[u'role'].encode('utf-8', 'xmlcharrefreplace')
                name = cast[u'name'].encode('utf-8', 'xmlcharrefreplace')
                item.AddCastAndRole(name, role)
                castList.append(name)
            item.SetProperty('cast', string.join(castList, ', '))

            for platform in movie[u'platforms']:
                item.SetProperty('on_%s' % platform.encode('ascii'), 'true')

            if movie[u'trailer']:
                url = movie[u'trailer'].encode('ascii')
                item.AddAlternativePath('Trailer', url, 'video/mp4', iconUrl)
                item.SetPath(url)
                item.SetContentType('video/mp4')
                item.SetProperty('hasTrailer', 'true')
            if movie[u'trailerLowRes']:
                item.AddAlternativePath('Trailer LowRes', movie[u'trailerLowRes'].encode('ascii'), 'video/mp4', iconUrl)
                item.SetProperty('hasTrailer', 'true')
            cnt = 0
            for shot in screenShots:
                url = shot[u'url'].encode('ascii')
                item.SetImage(cnt, url)
                item.SetProperty('image%i' % cnt, url)
                if cnt == 0:
                    item.SetIcon(url)
                cnt += 1
            item.SetProperty('ix', '%i' % item_cnt)

            items.append(item)
            item_cnt += 1
        movies = GetActiveWindow().GetList(200)
        movies.SetItems(items)
    finally:
        hideWaitDialog()
# -----------------------------------------------------------------------------
# Populate Controls
# -----------------------------------------------------------------------------
def populateGenre():
    jsonData = getURL(BASE_URL + "genres/1?type=movies")
    data = json.loads(jsonData)
    #pprint(data)
    items = mc.ListItems()
    global genreCache
    genreCache = {}
    for g in data[u'data']:
        #pprint(g)
        item = ListItem(ListItem.MEDIA_UNKNOWN)
        item.SetLabel(str(g[u'name']))
        item.SetProperty('value', str(g[u'value']))
        genreCache[g[u'value']] = item
        items.append(item)
    genre.SetItems(items)

def populateSorting():
    items = mc.ListItems()
    data = [{'name' : 'Alphabetical', 'value' : 'alphabetical'}, {'name' : 'Views', 'value' : 'views'}, {'name' : 'Rating', 'value' : 'rating'}]
    for g in data:
        if g['name']:
            item = ListItem(ListItem.MEDIA_UNKNOWN)
            item.SetLabel(g['name'])
            item.SetProperty('value', g['value'])
            items.append(item)
    sorting.SetItems(items)

def populateCategory():
    items = mc.ListItems()
    data = [{'name' : 'Free', 'value' : 'free'}, {'name' : 'Premium', 'value' : 'premium'}, {'name' : 'All', 'value' : 'all'}]
    for g in data:
        if g['name']:
            item = ListItem(ListItem.MEDIA_UNKNOWN)
            item.SetLabel(g['name'])
            item.SetProperty('value', g['value'])
            items.append(item)
    category.SetItems(items)

def populateControls():
    global genre, sorting, category
    # Initialize UI
    ShowDialogWait()
    try:
        genre = GetWindow(WINDOW_ID).GetList(201)
        sorting = GetWindow(WINDOW_ID).GetList(202)
        category = GetWindow(WINDOW_ID).GetList(203)
        populateSorting()
        populateCategory()
        populateGenre()
        restoreUserSettings()
    finally:
        hideWaitDialog()

# -----------------------------------------------------------------------------
# User Settings
# -----------------------------------------------------------------------------
editFields = {'username' : 501, 'password' : 502}
listFields = {'genre' : 201, 'sorting' : 202, 'type' : 203}
def restoreUserSettings():
    print "restoring user-settings"
    window = GetWindow(WINDOW_ID)
    config = GetApp().GetLocalConfig()
    for key, id in editFields.items():
        value = config.GetValue(key)
        if not value is None:
            window.GetEdit(id).SetText(value)
    for key, id in listFields.items():
        value = config.GetValue(key)
        if not value is None:
            window.GetList(id).SetFocusedItem(int(value))

def saveUserSettings():
    print "saving user-settings"
    window = GetWindow(WINDOW_ID)
    config = GetApp().GetLocalConfig()
    for key, id in editFields.items():
        value = window.GetEdit(id).GetText()
        if value:
            config.SetValue(key, value)
    for key, id in listFields.items():
        value = window.GetList(id).GetFocusedItem()
        if not value is None:
            config.SetValue(key, "%i" % value)

# -----------------------------------------------------------------------------
# Helper / Library Methods
# -----------------------------------------------------------------------------
def status(msg, progress=0, max=0):
    window = GetWindow(WINDOW_ID)
    label = window.GetLabel(STATUS_ID)
    image = window.GetImage(PROGRESS_ID)
    print(msg)
    label.SetLabel(msg)
    if max:
        ratio = math.ceil(progress*10/max)/2 # number between 0-5 with increments of .5
        texture = 'stars_%02i.png' % (ratio * 10)
        print "Texture: %s, %f" % (texture, ratio)
        image.SetTexture(texture)
        image.SetVisible(True)
    else:
        image.SetVisible(False)
    label.SetVisible(True)

def error(msg):
    ShowDialogOk("Error", msg)

def hideWaitDialog():
    window = GetWindow(WINDOW_ID)
    label = window.GetLabel(STATUS_ID)
    label.SetVisible(False)
    mc.HideDialogWait()

def getMovieURL(id):
    if PLAYER==1:
        sId = getSessionId()
        if sId:
            return PLAYER1_URL % (sId, id)
    elif PLAYER==2:
        token = getTokenId()
        if token:
            return PLAYER2_URL % (token, id)
    return None

def getGenres(genres):
    global genreCache
    if not genreCache:
        raise "genreCache not initialized!"
    genre = []
    for g in genres:
        if g in genreCache:
            genre.append(genreCache[g].GetLabel())
    return string.join(genre, ', ')

def _getListItemValue(list):
    focusIndex = list.GetFocusedItem()
    focusItem = list.GetItem(focusIndex)
    return focusItem.GetProperty('value')

def getGenre():
    global genre
    return _getListItemValue(genre)

def getSorting():
    global sorting
    return _getListItemValue(sorting)

def getCategory():
    global category
    return _getListItemValue(category)

def getURL(url):
    f = urllib2.urlopen(url)
    data = f.read()
    print url + ":\n" + data
    return data

def getSessionId():
    global sessionId
    if sessionId:
        return sessionId
    username = GetEdit(501).GetText()
    password = GetEdit(502).GetText()
    status("Logging in as %s" % username)
    jsonData = getURL(LOGIN_URL % (username, password))
    data = json.loads(jsonData)
    pprint(data)
    if data[u'success']:
        sessionId = data[u'data'][u'session'].encode('ascii')
    else:
        sessionId = None
        error("Error authenticating: %s" % data[u'message'].encode('ascii'))
    return sessionId

def getTokenId():
    status("Retrieving token");
    jsonData = getURL(TOKEN_URL % getSessionId())
    data = json.loads(jsonData)
    pprint(data)
    if data[u'success']:
        return data[u'data'][u'token'].encode('ascii')
    else:
        sessionId = None
        error("Error retrieving token: %s" % data[u'message'].encode('ascii'))
    return None

# Show the main window
mc.ActivateWindow(14000)
# restore default values
restoreUserSettings()