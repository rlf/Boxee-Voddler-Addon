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
PAGETYPE_LBL_ID=111

MOVIES_ID=200

GENRE_ID=201
SORTING_ID=202
CATEGORY_ID=203
PAGE_LABEL=110
STATUS_LABEL=120
TRAILER_WINDOW=14025

# Constants
pageSize=100
TIME_BETWEEN_SEARCHES = 3 # at least 3 seconds between searches - makes sure that we don't accidentially skip pages

# Global vars
pageCache = {}
currentMovieIndex = 1
currentPage = 0
lastPage = 0
maxPage = 0
maxCount = 0
lastSearch = 0

oldPageType = None
pageType = 'movie'

# -----------------------------------------------------------------------------
# Actions
# -----------------------------------------------------------------------------
def selectMovie(listId=MOVIES_ID):
    movieList = GetActiveWindow().GetList(listId)
    index = movieList.GetFocusedItem()
    movie = movieList.GetItem(index)

    ShowDialogWait()
    status("Playing movie %s" % movie.GetLabel())
    try:
        player = mc.GetApp().GetLocalConfig().GetValue('player')
        url = voddlerapi.getAPI().getMovieURL(movie.GetProperty('id'), player)
        trailerHD = movie.GetProperty('Trailer HD')
        trailerSD = movie.GetProperty('Trailer SD')
        urls = [url, trailerHD, trailerSD]
        if trailerHD or trailerSD:
            options = ['Movie']
            if trailerHD:
                options.append('Trailer HD')
            if trailerSD:
                options.append('Trailer SD')
            # TODO: I can't get this to work - Boxee raises some error (seems to be a Boxee Bug).
            # Perhaps http://jira.boxee.tv/browse/BOXEE-4540
            # Most likely we will get an "integrated popup" on LEFT instead...
            #selection = mc.ShowDialogSelect("Play", options)
            #url = urls[selection]
        hideWaitDialog()
        if not url:
            # revert to web-url
            url = movie.GetProperty('url')
        print "Playing %s" % url
        movie.SetPath(url)
        mc.GetPlayer().PlayWithActionMenu(movie)
    finally:
        hideWaitDialog()

def launchTrailer():
    ShowDialogWait()
    movieList = mc.GetActiveWindow().GetList(MOVIES_ID)
    index = movieList.GetFocusedItem()
    movie = movieList.GetItem(index)

    trailerHD = movie.GetProperty('Trailer HD')
    trailerSD = movie.GetProperty('Trailer SD')
    if trailerHD or trailerSD:
        status("Playing trailer for %s" % movie.GetLabel())
        trailer = ListItem(ListItem.MEDIA_VIDEO_TRAILER)
        trailer.SetLabel("Trailer for %s" % movie.GetLabel())
        if trailerHD:
            trailer.SetPath(trailerHD)
        elif trailerSD:
            trailer.Setpath(trailerSD)
            trailer.SetLabel("LQ %s" % trailer.GetLabel())
        mc.GetPlayer().Play(trailer)
    movieList.SetFocus()
    hideWaitDialog()

def search(reset=False):
    global maxPage, maxCount, currentPage, pageCache, lastPage, lastSearch
    api = voddlerapi.getAPI()
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
            maxCount, data = api.search(pageType, c, g, s, offset, pageSize)
            maxPage = (maxCount-1) / pageSize
            if maxPage < 0:
                maxPage = 0
            itemsOnCurrentPage = min(pageSize, maxCount, maxCount - (currentPage*pageSize))
            for index, movie in enumerate(data):
                status("Generating page %i of %i" % (currentPage+1, maxPage+1), index+1, itemsOnCurrentPage)
                item = ListItem(ListItem.MEDIA_VIDEO_FEATURE_FILM)
                movie.showOnListItem(item, index)
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

# -----------------------------------------------------------------------------
# Populate Controls
# -----------------------------------------------------------------------------
def populateGenre():
    genres = voddlerapi.getAPI().getGenres(pageType)
    #pprint(data)
    items = mc.ListItems()
    global genreCache
    genreCache = {}
    for value, name in genres.items():
        #pprint(g)
        item = ListItem(ListItem.MEDIA_UNKNOWN)
        item.SetLabel(name)
        item.SetProperty('value', value)
        genreCache[value] = item
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

def populateControls():
    # Initialize UI
    ShowDialogWait()
    try:
        window = GetActiveWindow()
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
    global pageSize, pageType, oldPageType
    print "restoring user-settings"
    window = GetWindow(WINDOW_ID)
    config = GetApp().GetLocalConfig()

    numPages = config.GetValue('pages')
    if numPages:
        pageSize = int(numPages)
    if pageType != oldPageType:
        return
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
    if not globals().has_key('genreCache'):
        return string.capwords(string.join(genres, ', ').encode('utf-8', 'xmlcharreplace'), ', ')
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
    global pageCache, currentPage, maxPage, pageType, oldPageType
    mc.GetActiveWindow().GetControl(1).SetVisible(False)
    mc.ShowDialogWait()
    pageType = mc.GetApp().GetLocalConfig().GetValue('pageType')
    if not pageType:
        pageType = 'movie'
    if oldPageType != pageType:
        pageCache = {} # force refresh
    pagetypes = {'movie' : 'Movies', 'episode' : 'TVSeries', 'documentary' : 'Documentaries'}
    mc.GetActiveWindow().GetLabel(PAGETYPE_LBL_ID).SetLabel(pagetypes[pageType])
    if not pageCache:
        populateControls()
        restoreUserSettings()
        search(True)
    else:
        # restore dynamic labels
        window = mc.GetActiveWindow()
        window.GetLabel(PAGE_LABEL).SetLabel("Page %i of %i" % (currentPage+1, maxPage+1))
        offset = currentPage * pageSize
        window.GetLabel(STATUS_LABEL).SetLabel("showing %i-%i of %i" % (offset+1, offset+len(pageCache[currentPage]), maxCount))
        window.GetLabel(USERNAME_LBL_ID).SetLabel(login.getLoggedIn())
    oldPageType = pageType
    hideWaitDialog()
    mc.GetActiveWindow().GetControl(1).SetVisible(True)

if __name__ == '__main__':
    # Show the main window
    mc.ActivateWindow(WINDOW_ID)
