# Main .py file
# TODOs
# * Localization - all strings in something else :D
# * Add to voddler playlist + favourite
# * Play trailer
import string, math
import mc
from mc import *
import time

from pprint import pprint

import login
from status import *
import voddlerapi

# IDs
WINDOW_ID=14000
USERNAME_LBL_ID=102

MOVIES_ID=200

GENRE_ID=201
SORTING_ID=202
CATEGORY_ID=203
PAGE_LABEL=110
STATUS_LABEL=120

# Constants
pageSize=100
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
        url = voddlerapi.getPlayerURL(movie.GetProperty('id'))
        hideWaitDialog()
        if not url:
            url = movie.GetProperty('url')
        print "Playing %s" % url
        movie.SetPath(url)
        GetPlayer().PlayWithActionMenu(movie)
    finally:
        hideWaitDialog()

def search(reset=False):
    global maxPage, maxCount, currentPage, pageCache, lastPage, lastSearch
    ShowDialogWait()
    status("Searching...")
    saveUserSettings()
    window = GetWindow(WINDOW_ID)
    mainList = window.GetList(MOVIES_ID)
    statusLabel = window.GetLabel(STATUS_LABEL)
    statusLabel.SetVisible(False)
    if reset:
        currentPage = 0
        pageCache = {}
        lastPage = 0
    try:
        g = getGenre()
        s = getSorting()
        c = getCategory()
        offset = currentPage * pageSize
        items = ListItems()
        if currentPage in pageCache.keys():
            items = pageCache[currentPage]
        else:
            status("Fetching page %i" % (currentPage+1))
            data = voddlerapi.searchVoddler('movie', c, g, s, offset, pageSize)
            maxCount = int(data[u'data'][u'count'])
            maxPage = (maxCount-1) / pageSize
            if maxPage < 0:
                maxPage = 0
            itemsOnCurrentPage = min(pageSize, maxCount, maxCount - (currentPage*pageSize))
            for index, movie in enumerate(data[u'data'][u'videos']):
                status("Genrating page %i of %i" % (currentPage+1, maxPage+1), index+1, itemsOnCurrentPage)
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
        window.GetLabel(PAGE_LABEL).SetLabel("Page %i of %i" % (currentPage+1, maxPage+1))
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
    item.SetProperty('url', movieUrl)
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
    data = voddlerapi.getGenres('movie')
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
    data = [{'name' : 'Rating', 'value' : 'rating'}, {'name' : 'Views', 'value' : 'views'}, {'name' : 'Alphabetical', 'value' : 'alphabetical'}]
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
    data = [{'name' : 'Free', 'value' : 'free'}, {'name' : 'Rent', 'value' : 'premium'}, {'name' : 'All', 'value' : 'all'}]
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
    print "restoring user-settings"
    window = GetWindow(WINDOW_ID)
    config = GetApp().GetLocalConfig()

    numPages = config.GetValue('pages')
    if numPages:
        pageSize = numPages
    for key, id in listFields.items():
        value = config.GetValue(key)
        print "restoring %s as %s" % (key, value)
        if value or value == 0:
            window.GetList(id).SetFocusedItem(int(value))
        window.GetList(id).SetVisible(True)

def saveUserSettings():
    print "saving user-settings"
    window = GetWindow(WINDOW_ID)
    config = GetApp().GetLocalConfig()
    for key, id in listFields.items():
        value = window.GetList(id).GetFocusedItem()
        config.SetValue(key, "%i" % value)

# -----------------------------------------------------------------------------
# Helper / Library Methods
# -----------------------------------------------------------------------------
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

def loadPage():
    global pageCache, currentPage, maxPage
    mc.GetActiveWindow().GetControl(1).SetVisible(False)
    mc.ShowDialogWait()
    if not pageCache:
        populateControls()
        restoreUserSettings()
        search(True)
    else:
        window = mc.GetActiveWindow()
        window.GetLabel(PAGE_LABEL).SetLabel("Page %i of %i" % (currentPage+1, maxPage+1))
        offset = currentPage * pageSize
        window.GetLabel(STATUS_LABEL).SetLabel("showing %i-%i of %i" % (offset+1, offset+len(pageCache[currentPage]), maxCount))
    hideWaitDialog()
    mc.GetActiveWindow().GetControl(1).SetVisible(True)

if __name__ == '__main__':
    # Show the main window
    mc.ActivateWindow(WINDOW_ID)