# Main .py file

import string, math
import mc
from mc import *
import urllib2
try: import json
except: import simplejson as json
from pprint import pprint

baseURL = "http://api.voddler.com/metaapi/"

# -----------------------------------------------------------------------------
# Actions
# -----------------------------------------------------------------------------
def selectGenre():
    print "selectGenre"

def selectSorting():
    print "selectSorting"

def selectMovie():
    movieList = GetActiveWindow().GetList(200)
    index = movieList.GetFocusedItem()
    movie = movieList.GetItem(index)
    GetPlayer().PlayWithActionMenu(movie)

def loadFanArt():
    print "loading fan art"

def search():
    ShowDialogWait()
    try:
        movies = GetActiveWindow().GetList(200)
        items = ListItems()
        movies.SetItems(items)

        g = getGenre()
        s = getSorting()
        c = getCategory()
        jsonData = getURL(baseURL + "browse/1?type=movie&category=" + c + "&genre=" + g + "&sort=" + s + "&offset=0&count=100");
        data = json.loads(jsonData)
        items = ListItems()
        item_cnt = 1
        for movie in data[u'data'][u'videos']:
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
            item.SetProperty('genres', getGenres(movie[u'genres']))
            item.SetProperty("details", "%s | %s" % (releaseYear, durationFormatted))
            item.SetDescription(description, True)
            #item.SetThumbnail(iconUrl)
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

            item.Dump()
            items.append(item)
            item_cnt += 1
        movies = GetActiveWindow().GetList(200)
        movies.SetItems(items)
    finally:
        HideDialogWait()
# -----------------------------------------------------------------------------
# Populate Controls
# -----------------------------------------------------------------------------
def populateGenre():
    jsonData = getURL(baseURL + "genres/1?type=movies")
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
        genre = GetWindow(14000).GetList(201)
        sorting = GetWindow(14000).GetList(202)
        category = GetWindow(14000).GetList(203)
        populateSorting()
        populateCategory()
        populateGenre()
    finally:
        HideDialogWait()

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


# Show the main window
mc.ActivateWindow(14000)