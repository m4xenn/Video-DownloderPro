"""Read WebView2 child frames in place, retaining their real parent/session.

Uses the host application's FrameCreated / ExecuteScriptAsync APIs. It exposes
no Python API to remote pages and changes no browser security settings.
Unsupported backends retain the bounded navigation fallback.
"""
import json
import threading


class NativeFrames:
    def __init__(self,window):
        self.window=window
        self.frames={}
        self.lock=threading.RLock()
        self.closed=False
        self.active=False
        self.requests={}
        self.request_ids={}
        self.extra_headers={}
        self.receivers=[]
        self.request_documents={}
        self.media_responses={}
        self.worker_sessions=set()

    def attach(self):
        try:
            from System import Func,Object
            self.control=self.window.native.webview
            self.scheduler=self.window.native.browser.syncContextTaskScheduler
            def install():
                core=self.control.CoreWebView2
                def prevent_popup(sender,args):args.Handled=True
                self.popup_handler=prevent_popup
                core.NewWindowRequested += prevent_popup
                core.FrameCreated += self._created
                try:
                    from Microsoft.Web.WebView2.Core import CoreWebView2WebResourceContext,CoreWebView2WebResourceRequestSourceKinds
                    core.AddWebResourceRequestedFilter('*',CoreWebView2WebResourceContext.All,CoreWebView2WebResourceRequestSourceKinds.All)
                except (ImportError,AttributeError,TypeError):
                    pass
                # OOPIF/worker requests may be absent from pywebview's legacy
                # resource events. Observe them through the host's in-process
                # protocol API; no remote debugging port is opened.
                try:
                    def protocol(method,params,session=''):
                        if session:return core.CallDevToolsProtocolMethodForSessionAsync(session,method,json.dumps(params))
                        return core.CallDevToolsProtocolMethodAsync(method,json.dumps(params))
                    def listen(name,handler):
                        receiver=core.GetDevToolsProtocolEventReceiver(name)
                        receiver.DevToolsProtocolEventReceived += handler
                        self.receivers.append((receiver,handler))
                    def attached(sender,args):
                        if self.closed:return
                        data=json.loads(args.ParameterObjectAsJson)
                        session=data.get('sessionId','')
                        if data.get('targetInfo',{}).get('type')=='worker' and len(self.worker_sessions)<64:
                            self.worker_sessions.add(session)
                        protocol('Network.enable',{},session)
                        protocol('Target.setAutoAttach',{'autoAttach':True,'waitForDebuggerOnStart':False,'flatten':True},session)
                    def requested(sender,args):
                        if self.closed:return
                        data=json.loads(args.ParameterObjectAsJson);request=data.get('request') or {}
                        url=request.get('url','')
                        if not url.startswith(('http://','https://')):return
                        with self.lock:
                            if len(self.requests)>=256:self.requests.pop(next(iter(self.requests)))
                            self.requests[url]={str(k):str(v) for k,v in request.get('headers',{}).items()}
                            key=(str(getattr(args,'SessionId','')),data.get('requestId'))
                            if len(self.request_ids)>=256:self.request_ids.pop(next(iter(self.request_ids)))
                            self.request_ids[key]=url
                            if len(self.request_documents)>=256:self.request_documents.pop(next(iter(self.request_documents)))
                            self.request_documents[key]=data.get('documentURL','')
                            self.requests[url].update(self.extra_headers.pop(key,{}))
                    def extra(sender,args):
                        if self.closed:return
                        data=json.loads(args.ParameterObjectAsJson)
                        key=(str(getattr(args,'SessionId','')),data.get('requestId'))
                        with self.lock:
                            url=self.request_ids.get(key)
                            headers={str(k):str(v) for k,v in data.get('headers',{}).items()}
                            if url in self.requests:self.requests[url].update(headers)
                            else:
                                if len(self.extra_headers)>=256:self.extra_headers.pop(next(iter(self.extra_headers)))
                                self.extra_headers[key]=headers
                    listen('Target.attachedToTarget',attached)
                    listen('Network.requestWillBeSent',requested)
                    listen('Network.requestWillBeSentExtraInfo',extra)
                    def response(sender,args):
                        if not self.closed:
                            self.observe_response(json.loads(args.ParameterObjectAsJson),str(getattr(args,'SessionId','')))
                    listen('Network.responseReceived',response)
                    protocol('Network.enable',{})
                    protocol('Target.setAutoAttach',{'autoAttach':True,'waitForDebuggerOnStart':False,'flatten':True})
                except Exception:
                    pass
                self.active=True
            self.control.Invoke(Func[Object](install))
        except Exception:
            self.active=False
        return self.active

    def observe_response(self,data,session=''):
        from services.network_media import media_kind
        response=data.get('response') or {}
        url=response.get('url','');mime=response.get('mimeType','');status=response.get('status')
        if not media_kind(url,mime,status):return
        with self.lock:
            if self.closed:return
            if len(self.media_responses)>=40:self.media_responses.pop(next(iter(self.media_responses)))
            self.media_responses[url]={'url':url,'mime':mime,'status':status,
                'worker':session in self.worker_sessions,
                'document':self.request_documents.get((session,data.get('requestId')),''),'resource_type':data.get('type','')}

    def network_candidates(self):
        with self.lock:
            items=[dict(item) for item in self.media_responses.values()]
            for item in items:item['headers']=self.headers([item['url']])[item['url']]
            return items

    def _created(self,sender,args,parent=None,depth=1):
        if self.closed or depth>3:return
        frame=args.Frame
        key=int(frame.GetHashCode())
        with self.lock:
            if len(self.frames)>=24:return
            entry={'frame':frame,'key':key,'parent':parent,'depth':depth,'pending':False,'snapshot':None,'alive':True}
            self.frames[key]=entry
        def child(sender,args):self._created(sender,args,key,depth+1)
        def destroyed(sender,args):
            with self.lock:
                entry['alive']=False
                self.frames.pop(key,None)
        # Keep delegates alive as long as the frame is alive.
        entry['child_handler']=child;entry['destroyed_handler']=destroyed
        try:
            frame.FrameCreated += child
            frame.Destroyed += destroyed
        except Exception:
            pass

    def read(self,script):
        if not self.active or self.closed:return []
        from System import Action,Func,Object,String
        from System.Threading.Tasks import Task
        done=threading.Event()
        pending=[]
        def schedule():
            with self.lock:
                entries=list(self.frames.values())
            for entry in entries:
                if entry['pending'] or not entry['alive']:continue
                entry['pending']=True
                pending.append(entry)
                def finish(task,target=entry):
                    try:
                        value=json.loads(task.Result)
                        if isinstance(value,dict) and target['alive'] and not self.closed:
                            target['snapshot']=value
                    except Exception:
                        pass
                    finally:
                        target['pending']=False
                        if all(not item['pending'] for item in pending):done.set()
                try:
                    entry['frame'].ExecuteScriptAsync(script).ContinueWith(Action[Task[String]](finish),self.scheduler)
                except Exception:
                    entry['pending']=False
            if all(not item['pending'] for item in pending):done.set()
        try:
            self.control.Invoke(Func[Object](schedule))
            done.wait(2)
        except Exception:
            return []
        with self.lock:
            return [{'key':entry['key'],'parent':entry['parent'],'snapshot':entry['snapshot']}
                    for entry in self.frames.values() if entry['alive'] and entry['snapshot']]

    def close(self):
        self.closed=True
        self.active=False
        with self.lock:
            self.frames.clear();self.requests.clear();self.request_ids.clear();self.extra_headers.clear();self.receivers.clear()
            self.media_responses.clear();self.request_documents.clear()
            self.worker_sessions.clear()

    def headers(self,sources):
        names={'referer':'Referer','origin':'Origin','user-agent':'User-Agent','cookie':'Cookie'}
        with self.lock:
            return {source:{names[k.lower()]:value for k,value in self.requests.get(source,{}).items() if k.lower() in names} for source in sources}


def merge_frames(root,frames):
    """Only visible player-frame branches from the DOM can supply candidates."""
    if not isinstance(root,dict):return root
    from services.media_discovery import public_url
    result=dict(root,media=list(root.get('media') or []),players=list(root.get('players') or []))
    allowed={};remaining=list(frames)
    for _ in range(3):
        for entry in list(remaining):
            parent=entry.get('parent')
            if parent is not None and parent not in allowed:continue
            data=entry.get('snapshot') or {}
            container=root if parent is None else allowed[parent][0]
            inherited=float('inf') if parent is None else allowed[parent][1]
            document=data.get('url')
            if not public_url(document):
                remaining.remove(entry);continue
            frame=next((frame for frame in container.get('embeds',[]) if isinstance(frame,dict) and frame.get('url','').split('#')[0]==document.split('#')[0]),None)
            if not frame:continue
            area=min(float(frame.get('area') or 0),inherited)
            if area<6000:
                remaining.remove(entry);continue
            allowed[entry['key']]=(data,area)
            remaining.remove(entry)
            if data.get('drm'):result['drm']=True
            if data.get('interaction'):result['interaction']=True
            if data.get('verification'):result['verification']=True
            for item in (data.get('players') or [])[:12]:
                record=dict(item,area=min(float(item.get('area') or 0),area))
                if record not in result['players']:result['players'].append(record)
            for item in (data.get('media') or [])[:8]:
                record=dict(item)
                record['area']=min(float(item.get('area') or area),area)
                if record not in result['media']:result['media'].append(record)
    return result
