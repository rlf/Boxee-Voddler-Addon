# login.py - all related to login

import mc, xbmc
from status import *
import urllib2
import time

import voddlerapi
from pprint import pprint

LOGIN_ID=14010

USERNAME_ID=501
PASSWORD_ID=502
LOGIN_BTN = 700
SESSION_TIMEOUT = 60*60*24 # 24 hr timeout - in reality it's indefinitely (or until another login has occurred).
sessionId = None
username = None
password = None
sessionTimestamp = 0
_callback = None

def loadLogin():
    global username, password
    window = mc.GetWindow(LOGIN_ID)
    if username:
        window.GetEdit(USERNAME_ID).SetText(username)
    if password:
        window.GetEdit(PASSWORD_ID).SetText(password)
    if username and password:
        window.GetControl(LOGIN_BTN).SetFocus()
    elif username:
        window.GetEdit(PASSWORD_ID).SetFocus()
    else:
        window.GetEdit(USERNAME_ID).SetFocus()

def unloadLogin():
    if _callback:
        _callback()

def exitLogin():
    xbmc.executebuiltin('Dialog.Close(%s)' % LOGIN_ID)
    mc.CloseWindow()

def getLoggedIn():
    global username, sessionId
    if sessionId and username:
        return username
    return ''

def restoreLoginSettings():
    global username, password, sessionId, sessionTimestamp
    config = mc.GetApp().GetLocalConfig()
    username = config.GetValue('username')
    password = config.GetValue('password')
    sessionId = config.GetValue('sessionId')
    sessionTimestamp = config.GetValue('sessionTimeStamp')
    if sessionTimestamp:
        sessionTimestamp = int(sessionTimestamp)

def saveLoginSettings():
    config = mc.GetApp().GetLocalConfig()
    global username, password, sessionId, sessionTimestamp
    if username is None:
        username = ''
    if password is None:
        password = ''
    config.SetValue('username', username)
    config.SetValue('password', password)
    if sessionId:
        config.SetValue('sessionId', sessionId)
        config.SetValue('sessionTimeStamp', '%i' % sessionTimestamp)
    else:
        config.SetValue('sessionId', '')
        config.SetValue('sessionTimeStamp', '0')

def textChanged():
    global username, password
    window = mc.GetWindow(LOGIN_ID)
    username = window.GetEdit(USERNAME_ID).GetText()
    password = window.GetEdit(PASSWORD_ID).GetText()

def logout():
    global sessionId, password, username
    oldSessionId = sessionId
    sessionId = None
    password = None
    saveLoginSettings()
    if oldSessionId:
        info("Logged %s out" % username)
    else:
        info("Logged out")

def login(callback=None):
    global _callback
    _callback = callback
    restoreLoginSettings()
    if not checkLogin():
        showLogin()
    elif _callback:
        _callback()

def showLogin():
    mc.ActivateWindow(LOGIN_ID)

def doLogin():
    global _callback
    mc.ShowDialogWait()
    if not checkLogin():
        mc.ActivateWindow(LOGIN_ID)
    else:
        saveLoginSettings()
        xbmc.executebuiltin('Dialog.Close(%s)' % LOGIN_ID)
        if _callback:
            _callback()
    hideWaitDialog()

def checkLogin():
    return getSessionId() != None

def getSessionId():
    global sessionId, username, password, sessionTimestamp
    if not (username and password):
        print "username or password was not set!"
        return None
    if sessionId and ((time.time() - sessionTimestamp) < SESSION_TIMEOUT):
        return sessionId
    status("Logging in as %s" % username)
    try:
        sessionId = voddlerapi.getAPI().login(username, password)
        if sessionId:
            sessionTimestamp = time.time()
            status("Successfully logged in as %s" % username)
        else:
            error("Error authenticating %s[CR][CR]%s" % (username, data[u'message']))
    except urllib2.HTTPError, e:
        sessionId = None
        error("Error authenticating %s[CR][CR]%s" % (username, e))
    return sessionId
