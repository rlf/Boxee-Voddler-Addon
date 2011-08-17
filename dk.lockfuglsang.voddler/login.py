# login.py - all related to login

import mc
from status import *
import urllib2
import urllib
try: import json
except: import simplejson as json

import voddlerapi
from pprint import pprint

LOGIN_ID=14010

USERNAME_ID=501
PASSWORD_ID=502
LOGIN_URL = "https://api.voddler.com/userapi/login/1"
TOKEN_URL = "https://api.voddler.com/userapi/vnettoken/1"

sessionId = None
username = None
password = None

def getLoggedIn():
    global username, sessionId
    if sessionId and username:
        return username
    return ''

def restoreLoginSettings():
    global username, password
    config = mc.GetApp().GetLocalConfig()
    username = config.GetValue('username')
    password = config.GetValue('password')

def saveLoginSettings():
    config = mc.GetApp().GetLocalConfig()
    global username, password
    if username is None:
        username = ''
    if password is None:
        password = ''
    config.SetValue('username', username)
    config.SetValue('password', password)

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
        status("Logged %s out" % username)
    else:
        status("Logged out")

def login():
    restoreLoginSettings()
    showLogin()

def showLogin():
    global username, password
    mc.ActivateWindow(LOGIN_ID)
    window = mc.GetWindow(LOGIN_ID)
    window.GetEdit(USERNAME_ID).SetText(username)
    window.GetEdit(PASSWORD_ID).SetText(password)

def doLogin():
    mc.ShowDialogWait()
    saveLoginSettings()
    if not checkLogIn():
        mc.ActivateWindow(LOGIN_ID)
    hideWaitDialog()

def checkLogIn():
    return getSessionId() != None

def getSessionId():
    global sessionId, username, password
    if not (username and password):
        print "username or password was not set!"
        return None
    if sessionId:
        return sessionId
    status("Logging in as %s" % username)
    try:
        jsonData = voddlerapi.getURL(LOGIN_URL, urllib.urlencode({'username' : username, 'password' : password}))
        data = json.loads(jsonData)
        pprint(data)
        if data[u'success']:
            sessionId = data[u'data'][u'session'].encode('ascii')
            status("Successfully logged in as %s" % username)
        else:
            sessionId = None
            error("Error authenticating %s[CR][CR]%s" % (username, data[u'message']))
    except urllib2.HTTPError, e:
        sessionId = None
        error("Error authenticating %s[CR][CR]%s" % (username, e))
    return sessionId

def getTokenId():
    status("Retrieving token");
    sessionId = getSessionId()
    if not sessionId:
        return None
    jsonData = voddlerapi.getURL(TOKEN_URL, urllib.urlencode({'session' : sessionId}))
    data = json.loads(jsonData)
    pprint(data)
    if data[u'success']:
        return data[u'data'][u'token'].encode('ascii')
    else:
        sessionId = None
        error("Error retrieving token: %s" % data[u'message'].encode('ascii'))
    return None
