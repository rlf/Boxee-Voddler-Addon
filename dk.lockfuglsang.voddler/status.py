# status.py - status methods
import mc

STATUS_ID = 14020
def error(msg):
    print "%s" % msg
    mc.ShowDialogNotification("%s" % msg)

def status(msg, cnt=0, max=0):
#    if not mc.Window.IsActive(STATUS_ID):
#        mc.ActivateWindow(STATUS_ID)
    if max:
        print "%s, %i of %i" % (msg, cnt, max)
    else:
        print "%s" % msg
    mc.ShowDialogNotification("%s" % msg)

def hideWaitDialog():
#    if mc.Window.IsActive(STATUS_ID):
#        mc.CloseWindow()
    mc.HideDialogWait()
