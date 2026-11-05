"""Per-downloader HTTP guards; no global socket or library monkeypatches."""
import ipaddress
import socket
from contextvars import ContextVar
from types import MethodType
from urllib.parse import urlsplit,urljoin
from services.security_policy import require_public_link,UnsafeLink,global_address

_curl_proxy=ContextVar('vdp_curl_proxy',default=False)


def preferred_address(addresses):
    return next((address for address in addresses if ':' not in address),addresses[0])


def public_addresses(host,port):
    addresses=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
    if not addresses or any(not global_address(item[4][0]) for item in addresses):
        raise UnsafeLink()
    return list(dict.fromkeys(item[4][0] for item in addresses))


def pin_requests_session(session):
    """Pin connections to validated IPs, retaining original TLS hostname/SNI."""
    from urllib3.connection import HTTPConnection,HTTPSConnection
    from urllib3.connectionpool import HTTPConnectionPool,HTTPSConnectionPool
    from urllib3.util.connection import create_connection
    class PublicConnection:
        def _new_conn(self):
            if getattr(self,'proxy',None):
                # The configured proxy is trusted infrastructure. The origin is
                # pinned in the HTTP request target or CONNECT tunnel below.
                return create_connection((self._dns_host,self.port),self.timeout,self.source_address,self.socket_options)
            last=None
            for address in public_addresses(self._dns_host,self.port):
                try:return create_connection((address,self.port),self.timeout,self.source_address,self.socket_options)
                except OSError as exc:last=exc
            raise last or UnsafeLink()
        def set_tunnel(self,host,port=None,headers=None,**kwargs):
            target=preferred_address(public_addresses(host,port or 443))
            self.server_hostname=host
            return super().set_tunnel(target,port=port,headers=headers,**kwargs)
    class PublicHTTPConnection(PublicConnection,HTTPConnection):pass
    class PublicHTTPSConnection(PublicConnection,HTTPSConnection):pass
    class PublicHTTPPool(HTTPConnectionPool):ConnectionCls=PublicHTTPConnection
    class PublicHTTPSPool(HTTPSConnectionPool):ConnectionCls=PublicHTTPSConnection
    classes={'http':PublicHTTPPool,'https':PublicHTTPSPool}
    for adapter in session.adapters.values():
        adapter.poolmanager.pool_classes_by_scheme=classes
        proxy_manager_for=adapter.proxy_manager_for
        # Bind each adapter's methods independently (the closures outlive this loop).
        def install_proxy_manager(original):
            def manager(proxy,**kwargs):
                result=original(proxy,**kwargs);result.pool_classes_by_scheme=classes;return result
            return manager
        adapter.proxy_manager_for=install_proxy_manager(proxy_manager_for)
        def install_request_url(original):
            def request_url(request,proxies):
                target=original(request,proxies)
                if target.startswith(('http://','https://')):
                    parsed=urlsplit(target);port=parsed.port or 80
                    address=preferred_address(public_addresses(parsed.hostname,port))
                    authority=f'[{address}]' if ':' in address else address
                    if parsed.port:authority+=':'+str(parsed.port)
                    request.headers['Host']=parsed.netloc
                    target=parsed._replace(netloc=authority).geturl()
                return target
            return request_url
        adapter.request_url=install_request_url(adapter.request_url)
    send=session.send
    def guarded_send(request,**kwargs):
        require_public_link(request.url,resolve=bool(kwargs.get('proxies')))
        # Session.send calls this same method for each redirect. Socket pinning
        # then checks the address actually used, including DNS rebinding.
        return send(request,**kwargs)
    session.send=guarded_send
    return session


def pin_curl_session(session):
    from curl_cffi.const import CurlOpt
    request=session.request
    def guarded_request(method,url,**kwargs):
        kwargs=dict(kwargs,allow_redirects=False)
        headers=dict(kwargs.get('headers') or {})
        for index in range(6):
            connect_pin=None
            require_public_link(url)
            parsed=urlsplit(url)
            canonical=parsed.hostname if ':' in parsed.hostname else parsed.hostname.encode('idna').decode('ascii')
            authority=f'[{canonical}]' if ':' in canonical else canonical
            if parsed.port:authority+=':'+str(parsed.port)
            url=parsed._replace(netloc=authority).geturl()
            require_public_link(url)
            parsed=urlsplit(url);port=parsed.port or (443 if parsed.scheme=='https' else 80)
            addresses=public_addresses(parsed.hostname,port)
            host=f'[{parsed.hostname}]' if ':' in parsed.hostname else parsed.hostname
            options=getattr(session,'curl_options',None)
            if isinstance(options,dict):
                options.pop(CurlOpt.CONNECT_TO,None);options.pop(CurlOpt.REQUEST_TARGET,None)
            def option(key,value):
                # Streaming requests clone/reset curl handles. Apply pins on the
                # transfer handle as well as the session's current handle.
                if isinstance(options,dict):options[key]=value
                session.curl.setopt(key,value)
            option(CurlOpt.RESOLVE,[f'{host}:{port}:'+','.join(f'[{ip}]' if ':' in ip else ip for ip in addresses)])
            configured=kwargs.get('proxy') or kwargs.get('proxies') or getattr(session,'proxies',None)
            using_proxy=_curl_proxy.get() or isinstance(configured,(dict,str)) and bool(configured)
            if using_proxy:
                address=preferred_address(addresses)
                numeric=f'[{address}]' if ':' in address else address
                if parsed.scheme=='https':
                    # curl_cffi treats CONNECT_TO as a raw slist pointer.
                    # Keep its lifetime attached to the actual stream handle.
                    from curl_cffi import ffi,lib
                    rule=f'{host}:{port}:{numeric}:{port}'.encode('ascii')
                    connect_pin=ffi.gc(lib.curl_slist_append(ffi.NULL,rule),lib.curl_slist_free_all)
                    option(CurlOpt.CONNECT_TO,connect_pin)
                else:
                    authority=numeric+(':'+str(parsed.port) if parsed.port else '')
                    option(CurlOpt.REQUEST_TARGET,parsed._replace(netloc=authority).geturl())
                    headers['Host']=parsed.netloc
            response=request(method=method,url=url,**dict(kwargs,headers=headers))
            if connect_pin is not None:
                response.curl._vdp_connect_pin=connect_pin
            location=response.headers.get('Location')
            if response.status_code not in (301,302,303,307,308) or not location:return response
            target=urljoin(url,location)
            status=response.status_code
            response.close()
            require_public_link(target)
            if index==5:raise UnsafeLink()
            if urlsplit(target).netloc!=parsed.netloc or urlsplit(target).scheme!=parsed.scheme:
                headers={k:v for k,v in headers.items() if k.lower() not in ('authorization','cookie','proxy-authorization','host')}
            if status==303 and method!='HEAD' or status in (301,302) and method=='POST':
                method='GET';kwargs.pop('data',None)
                headers={k:v for k,v in headers.items() if k.lower() not in ('content-type','content-length')}
            url=target
        raise UnsafeLink()
    session.request=guarded_request
    return session


def attach_network_guard(ydl):
    if getattr(ydl,'_vdp_network_guard',False) or not hasattr(ydl,'build_request_director'):return
    ydl._vdp_network_guard=True
    build=ydl.build_request_director
    def secure_build(self,handlers,preferences=None):
        secured=[]
        for handler in handlers:
            key=handler.RH_KEY
            if key not in ('Requests','CurlCFFI'):continue
            def create(instance,*args,_base=handler,_key=key,**kwargs):
                session=_base._create_instance(instance,*args,**kwargs)
                return pin_requests_session(session) if _key=='Requests' else pin_curl_session(session)
            def send(instance,request,_base=handler,_key=key):
                token=None
                if _key=='CurlCFFI':
                    from yt_dlp.utils.networking import select_proxy
                    token=_curl_proxy.set(bool(select_proxy(request.url,proxies=instance._get_proxies(request))))
                try:return _base._send(instance,request)
                except UnsafeLink as exc:
                    from yt_dlp.networking.exceptions import RequestError
                    raise RequestError(str(exc)) from exc
                finally:
                    if token is not None:_curl_proxy.reset(token)
            # Keep RH keys, impersonation capabilities and preference selection.
            secured.append(type(handler.__name__,(handler,),{'_create_instance':create,'_send':send}))
        if not secured:raise UnsafeLink()
        return build(secured,preferences)
    ydl.build_request_director=MethodType(secure_build,ydl)
    director=vars(ydl).pop('_request_director',None)
    if director:director.close()
