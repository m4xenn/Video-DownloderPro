"""Real WebView2 close veto/save/close events; dialogs use fixture answers."""
import json,sys,threading,time
from pathlib import Path
from unittest.mock import Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import webview
from services.app_lifecycle import ShutdownController,lifecycle_text
folder=ROOT/'build/lifecycle-native';folder.mkdir(exist_ok=True)
window=webview.create_window('Isolated VDP lifecycle acceptance',html='<p>Lifecycle acceptance</p>',hidden=True)
manager=Mock();manager.busy.return_value=True
saved=threading.Event();closed=threading.Event();calls=[];failures=[]
def save():time.sleep(.15);saved.set()
manager.close.side_effect=save
def confirm(title,message):
 calls.append((title,message));return len(calls)>1
window.create_confirmation_dialog=confirm
controller=ShutdownController(window,manager,lambda:calls.append('cleanup'),lambda:lifecycle_text('tr'))
window.events.closing+=controller.on_closing
window.events.closed+=lambda:closed.set()
def test():
 try:
  window.events.loaded.wait(10)
  window.destroy();time.sleep(.2)
  assert not closed.is_set(),'Cancel did not veto close'
  assert not saved.is_set(),'Cancelled close stopped downloads'
  assert window.evaluate_js('1+1')==2,'Window not usable after cancel'
  window.destroy()
  assert closed.wait(15),'Confirmed close did not finish'
  assert saved.is_set(),'Window closed before save'
  assert manager.close.call_count==1
  assert len([c for c in calls if isinstance(c,tuple)])==2
 except Exception as error:
  failures.append(str(error));controller.allowed=True;window.destroy()
webview.start(test,gui='edgechromium')
result={'passed':not failures,'errors':failures,'checks':['native cancel veto','usable window after cancel','confirmed asynchronous shutdown','saved before closed']}
(folder/'result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result));assert not failures,failures
