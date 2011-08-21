# playlists.py - UI python code for the playlists
import mc
import voddlerapi
import movies
listTypes = {'favorites' : 'Favorites', 'playlist' : 'Playlist', 'history' : 'History'}

listType = 'favorites'
oldListType = None
playlists = {}
movieList = {}

def loadPage():
    global listType, playlists, movieList, oldListType
    conf = mc.GetApp().GetLocalConfig()
    type = conf.GetValue('pageType')
    if type:
        listType = type
    sort = conf.GetValue('sort')
    if not sort:
        sort = 'alphabetical'
    window = mc.GetActiveWindow()
    window.GetLabel(111).SetLabel(listTypes[listType])
    if (oldListType is not listType) and not movieList.has_key(listType):
        movies.populateSorting()
        # do the search
        playlists = voddlerapi.getAPI().getPlaylists()
        playlist = voddlerapi.getAPI().getVideosForPlaylist(playlists[listType]['videos'], sort)
        items = mc.ListItems()
        for ix, movie in enumerate(playlist):
            item = mc.ListItem(mc.ListItem.MEDIA_VIDEO_FEATURE_FILM)
            movie.showOnListItem(item, ix)
            items.append(item)
        movieList[listType] = items
    videos = movieList[listType]
    window.GetList(200).SetItems(videos)
    if len(videos) > 0:
        window.GetLabel(120).SetLabel("Showing %i movies" % len(videos))
    else:
        window.GetLabel(120).SetLabel("No movies found in %s" % listType)
    oldListType = listType
