# moviepopup.py - options for movies

import mc, xbmc, movies

POPUP_ID = 14015
OPTIONS_LIST = 215
def load():
    # this should be the "main" window?
    window = mc.GetActiveWindow()
    list = window.GetList(movies.MOVIES_ID)
    index = list.GetFocusedItem()
    movie = list.GetItem(index)
    if not movie:
        mc.ShowNotificationDialog('No movie selected')
        xbmc.executebuiltin('Dialog.Close(%s)' % POPUP_ID)
        return
    popup = mc.GetWindow(POPUP_ID)
    options = popup.GetList(OPTIONS_LIST)
    # build options
    items = mc.ListItems()
    items.append(createItem('play', 'Play'))
    if movie.GetProperty('hasTrailer'):
        items.append(createItem('playTrailer', 'Play Trailer'))

    if movie.GetProperty('isFavorites') == 'true':
        items.append(createItem('rm:favorites', 'Remove from Favorites'))
    else:
        items.append(createItem('add:favorites', 'Add to Favorites'))
    if movie.GetProperty('isPlaylist') == 'true':
        items.append(createItem('rm:playlist', 'Remove from Playlist'))
    else:
        items.append(createItem('add:playlist', 'Add to Playlist'))
    options.SetItems(items)
    options.SetVisible(True)
    options.SetFocus()

def createItem(value, label, icon=None):
    item = mc.ListItem(mc.ListItem.MEDIA_UNKNOWN)
    item.SetPath(value)
    item.SetLabel(label)
    if icon:
        item.SetIcon(icon)
    return item

def optionClicked():
    popup = mc.GetWindow(POPUP_ID)
    options = popup.GetList(OPTIONS_LIST)
    option = options.GetItem(options.GetFocusedItem())
    cmd = option.GetPath()
    if cmd == 'play':
        movies.playMovie()
    elif cmd == 'playTrailer':
        movies.playTrailer()
    elif cmd.startswith('add:'):
        movies.addToPlaylist(cmd[4:])
    elif cmd.startswith('rm:'):
        movies.removeFromPlaylist(cmd[3:])
    xbmc.executebuiltin('Dialog.Close(%s)' % POPUP_ID)