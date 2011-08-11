import mc
def login():
   uname = mc.ShowDialogKeyboard("Enter Username", "")
   pword = mc.ShowDialogKeyboard("Enter Password", "", True)
   if uname and pword:
      http = mc.Http()
      params = "&cc_user_username=[%s]&cc_user_password=[%s]" % (uname, pword)
      http.Post("http://www.voddler.com/en/user/authenticate/?urlok=/en/", params)
      responseCookie = str(http.GetHttpHeader("Set-cookie"))
      if 'PHPSESSID=' in responseCookie:
         return True
   return False