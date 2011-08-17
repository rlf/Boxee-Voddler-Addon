import mc
import login

def load():
    if not login.getLoggedIn():
        login.login()
    updateLoginLabel()

def updateLoginLabel():
    if login.getLoggedIn():
        mc.GetActiveWindow().GetLabel(102).SetLabel(login.getLoggedIn())
    else:
        mc.GetActiveWindow().GetLabel(102).SetLabel("")

def selectWindow():
    list = mc.GetActiveWindow().GetList(100)
    items = list.GetItems()
    item = items[list.GetFocusedItem()]
    label = item.GetLabel()
    windows = {'Movies' : 14000}
    if label in windows:
        mc.ActivateWindow(windows[label])
    elif label == 'Login':
        login.login()
        updateLoginLabel()
    elif label == 'Logout':
        login.logout()
        updateLoginLabel()
    else:
        print "No window defined yet for %s" % label

