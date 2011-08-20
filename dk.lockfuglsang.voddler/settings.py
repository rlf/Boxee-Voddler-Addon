# settings.py - UI for settings

import mc

CONFIG = {'player' : 1001, 'pages' : 1002}
DEFAULTS = {'player' : 'embed', 'pages' : '100'}
def loadPage():
    window = mc.GetActiveWindow()
    config = mc.GetApp().GetLocalConfig()
    for key, listid in CONFIG.items():
        value = config.GetValue(key)
        if value is None:
            value = DEFAULTS[key]
        list = window.GetList(listid)
        for index, item in enumerate(list.GetItems()):
            if item.GetPath() == value:
                list.SetFocusedItem(index)
                break

def saveSettings():
    window = mc.GetActiveWindow()
    config = mc.GetApp().GetLocalConfig()
    for key, listid in CONFIG.items():
        try:
            list = window.GetList(listid)
            value = list.GetItem(list.GetFocusedItem()).GetPath()
            config.SetValue(key, value)
            mc.ShowDialogNotification("Settings saved")
        except:
            print "Settings not saved - dialog was closed too fast"


