import mc
import login

def load():
    if not login.getLoggedIn():
        login.login(lambda: postLogin())
    else:
        postLogin()

def postLogin():
    if login.getLoggedIn():
        mc.GetActiveWindow().GetLabel(102).SetLabel(login.getLoggedIn())
        mc.GetActiveWindow().GetControl(100).SetFocus()
    else:
        mc.GetActiveWindow().GetLabel(102).SetLabel("")
        login.login(lambda: postLogin())

def selectWindow():
    list = mc.GetActiveWindow().GetList(100)
    items = list.GetItems()
    item = items[list.GetFocusedItem()]
    label = item.GetLabel()
    windows = {'Movies' : 14000, 'Settings' : 14009}
    if label in windows:
        mc.ActivateWindow(windows[label])
    elif label == 'Logout':
        login.logout()
        postLogin()
    else:
        print "No window defined yet for %s" % label

