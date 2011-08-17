# Main .py file
# TODOs
# * Localization - all strings in something else :D
# * Add to voddler playlist + favourite
# * Play trailer
import string, math
import mc
from mc import *
import urllib
import urllib2
import time

try: import json
except: import simplejson as json
from pprint import pprint

import login

# IDs
WINDOW_ID=14000
STATUS_ID=100
PROGRESS_ID=600
USERNAME_LBL_ID=102

MOVIES_ID=200

GENRE_ID=201
SORTING_ID=202
CATEGORY_ID=203

# URLs
BASE_URL = "http://api.voddler.com/metaapi/"
SEARCH_URL = BASE_URL + "browse/1?type=movie&category=%s&genre=%s&sort=%s&offset=%i&count=%s"
PLAYER1_URL = "https://www.voddler.com/playapi/embedded/1?session=%s&videoId=%s&format=html"
PLAYER2_URL = "http://player.voddler.com/VoddlerPlayer.swf?vnettoken=%s&videoId=%s"

# Constants
PLAYER=1
PAGE_SIZE=50
PLATFORMS = ['iphone', 'web', 'android', 'symbian']
TIME_BETWEEN_SEARCHES = 3 # at least 3 seconds between searches - makes sure that we don't accidentially skip pages

# Global vars
pageCache = {}
currentMovieIndex = 1
currentPage = 0
lastPage = 0
maxPage = 0
maxCount = 0
lastSearch = 0
# -----------------------------------------------------------------------------
# Actions
# -----------------------------------------------------------------------------
def selectMovie(listId=200):
    movieList = GetActiveWindow().GetList(listId)
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

def search(reset=False):
    global maxPage, maxCount, currentPage, pageCache, lastPage, lastSearch
    ShowDialogWait()
    saveUserSettings()
    window = GetWindow(WINDOW_ID)
    mainList = window.GetList(MOVIES_ID)
    statusLabel = window.GetLabel(120)
    statusLabel.SetVisible(False)
    if reset:
        currentPage = 0
        pageCache = {}
        lastPage = 0
    try:
        g = urllib.quote(getGenre())
        s = urllib.quote(getSorting())
        c = urllib.quote(getCategory())
        offset = currentPage * PAGE_SIZE
        items = ListItems()
        if currentPage in pageCache.keys():
            items = pageCache[currentPage]
        else:
            status("Fetching page %i" % (currentPage+1))
            jsonData = getURL(SEARCH_URL % (c, g, s, offset, PAGE_SIZE));
            data = json.loads(jsonData)
            maxCount = int(data[u'data'][u'count'])
            maxPage = (maxCount-1) / PAGE_SIZE
            if maxPage < 0:
                maxPage = 0
            itemsOnCurrentPage = min(PAGE_SIZE, maxCount, maxCount - (currentPage*PAGE_SIZE))
            for index, movie in enumerate(data[u'data'][u'videos']):
                status("Generating page %i of %i" % (currentPage+1, maxPage+1), index+1, itemsOnCurrentPage)
                item = ListItem(ListItem.MEDIA_VIDEO_FEATURE_FILM)
                showMovieOnListItem(item, movie, index + offset)
                items.append(item)
            pageCache[currentPage] = items

        mainList.SetItems(items)
        if len(items) == 0:
            statusLabel.SetLabel("no movies found")
            mainList.SetVisible(False)
        else:
            statusLabel.SetLabel("showing %i-%i of %i" % (offset+1, offset+len(items), maxCount))
            mainList.SetVisible(True)
        statusLabel.SetVisible(True)
        window.GetLabel(110).SetLabel("Page %i of %i" % (currentPage+1, maxPage+1))
    finally:
        hideWaitDialog()
        if mainList.IsVisible():
            mainList.SetFocus()
        lastPage = currentPage
        print "search complete"
        lastSearch = time.time()

''' Makes sure that we don't accidentially spawn multiple searches due to
    erradic navigation.
'''
def isSearchAllowed():
    global lastSearch
    return time.time() - lastSearch > TIME_BETWEEN_SEARCHES

def nextPage():
    global currentPage, maxPage
    if not isSearchAllowed():
        return
    if currentPage < maxPage:
        currentPage += 1
        search()
    else:
        currentPage = 0
        search()
    GetWindow(WINDOW_ID).GetList(MOVIES_ID).SetFocusedItem(0)

def prevPage():
    global currentPage, maxPage
    if not isSearchAllowed():
        return
    if currentPage > 0:
        currentPage -= 1
        search()
    else:
        currentPage = maxPage
        search()
    list = GetWindow(WINDOW_ID).GetList(MOVIES_ID)
    list.SetFocusedItem(len(list.GetItems())-1)

def showMovieOnListItem(item, movie, index):
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
    item.SetProperty('rating', "%02i" % (math.floor(rating * 20) / 2))
    castList = []
    for cast in movie[u'castMembers']:
        role = cast[u'role'].encode('utf-8', 'xmlcharrefreplace')
        name = cast[u'name'].encode('utf-8', 'xmlcharrefreplace')
        item.AddCastAndRole(name, role)
        castList.append(name)

    item.SetProperty('cast', string.join(castList, ', '))
    for platform in PLATFORMS:
        item.SetProperty('on_%s' % platform, 'false')
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
        cnt += 1

    item.SetProperty('ix', "%i" % (index+1))

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
    genre = mc.GetActiveWindow().GetList(GENRE_ID)
    genre.SetItems(items)

def populateSorting():
    items = mc.ListItems()
    data = [{'name' : 'Alphabetical', 'value' : 'alphabetical'}, {'name' : 'Views', 'value' : 'views'}, {'name' : 'Rating', 'value' : 'rating'}]
    for g in data:
        if g['name']:
            item = ListItem(ListItem.MEDIA_UNKNOWN)
            item.SetLabel(g['name'])
            item.SetProperty('value', g['value'])
            item.SetIcon("sort_%s_on.png" % g['value'])
            item.SetThumbnail("sort_%s.png" % g['value'])
            items.append(item)
    mc.GetActiveWindow().GetList(SORTING_ID).SetItems(items)

def populateCategory():
    items = mc.ListItems()
    data = [{'name' : 'All', 'value' : 'all'}, {'name' : 'Rent', 'value' : 'premium'}, {'name' : 'Free', 'value' : 'free'}]
    for g in data:
        if g['name']:
            item = ListItem(ListItem.MEDIA_UNKNOWN)
            item.SetLabel(g['name'])
            item.SetProperty('value', g['value'])
            items.append(item)
    mc.GetActiveWindow().GetList(CATEGORY_ID).SetItems(items)

def populateLists():
    window = GetWindow(WINDOW_ID)
    list = window.GetList(MOVIES_ID)
    items = ListItems()
    item = ListItem(ListItem.MEDIA_VIDEO_FEATURE_FILM)
    items.append(item)
    list.SetItems(items)
    list.SetVisible(False)

def populateControls():
    # Initialize UI
    ShowDialogWait()
    try:
        window = GetActiveWindow()
        for id in [GENRE_ID, SORTING_ID, CATEGORY_ID]:
            window.GetList(id).SetVisible(False)
        if login.getLoggedIn():
            window.GetLabel(USERNAME_LBL_ID).SetLabel(login.getLoggedIn())
        populateSorting()
        populateCategory()
        populateGenre()
        populateLists()
        restoreUserSettings()
    finally:
        hideWaitDialog()

# -----------------------------------------------------------------------------
# User Settings
# -----------------------------------------------------------------------------
listFields = {'genre' : 201, 'sorting' : 202, 'type' : 203}
def restoreUserSettings():
    global autoLogin
    print "restoring user-settings"
    window = GetWindow(WINDOW_ID)
    config = GetApp().GetLocalConfig()

#    for key, id in editFields.items():
#        value = config.GetValue(key)
#        if not value is None:
#            GetWindow(LOGIN_ID).GetEdit(id).SetText(value)

    for key, id in listFields.items():
        value = config.GetValue(key)
        print "restoring %s as %s" % (key, value)
        if value or value == 0:
            window.GetList(id).SetFocusedItem(int(value))
        window.GetList(id).SetVisible(True)
    autoLogin = (config.GetValue('autoLogin') == 'True')

def saveUserSettings():
    global autoLogin
    print "saving user-settings"
    window = GetWindow(WINDOW_ID)
    config = GetApp().GetLocalConfig()
#    for key, id in editFields.items():
#        value = GetWindow(LOGIN_ID).GetEdit(id).GetText()
#        config.SetValue(key, value)
    for key, id in listFields.items():
        value = window.GetList(id).GetFocusedItem()
        config.SetValue(key, "%i" % value)
    config.SetValue('autoLogin', "%s" % autoLogin)

# -----------------------------------------------------------------------------
# Helper / Library Methods
# -----------------------------------------------------------------------------
def status(msg, progress=0, max=0):
    window = GetWindow(WINDOW_ID)
    label = window.GetLabel(STATUS_ID)
    image = window.GetImage(PROGRESS_ID)
    #print(msg)
    label.SetLabel(msg)
    if max:
        ratio = math.ceil(progress*10/max)/2 # number between 0-5 with increments of .5
        texture = 'stars_%02i.png' % (ratio * 10)
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

def _getListItemValue(listId):
    list = GetActiveWindow().GetList(listId)
    focusIndex = list.GetFocusedItem()
    focusItem = list.GetItem(focusIndex)
    return focusItem.GetProperty('value')

def getGenre():
    return _getListItemValue(GENRE_ID)

def getSorting():
    return _getListItemValue(SORTING_ID)

def getCategory():
    return _getListItemValue(CATEGORY_ID)

def getURL(url, postData=None):
    f = urllib2.urlopen(url, postData)
    data = f.read()
    print url + ":\n" + data
    return data

def loadPage():
    mc.GetActiveWindow().GetControl(1).SetVisible(False)
    mc.ShowDialogWait()
    populateControls()
    restoreUserSettings()
    search(True)
    hideWaitDialog()
    mc.GetActiveWindow().GetControl(1).SetVisible(True)

if __name__ == '__main__':
    # Show the main window
    mc.ActivateWindow(WINDOW_ID)