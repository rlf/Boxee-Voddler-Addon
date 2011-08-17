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
    print "settings loaded"

def saveSettings():
    print "saving settings"
    window = mc.GetActiveWindow()
    config = mc.GetApp().GetLocalConfig()
    for key, listid in CONFIG.items():
        try:
            list = window.GetList(listid)
            value = list.GetItem(list.GetFocusedItem()).GetPath()
            print "saving %s : %s" % (key, value)
            config.SetValue(key, value)
        except:
            print "error saving"


