"""Native extraction, player adapters, and bounded generic discovery fallback."""
import base64
import binascii
import ipaddress
import re
import threading
import time
from urllib.parse import urlsplit, urljoin

import requests
from bs4 import BeautifulSoup
from services.site_browser import site_browser

PAGE_HOSTS = {'fullhdfilmizlesene.now', 'www.fullhdfilmizlesene.now'}
EMBED_HOSTS = {'rapidvid.net', 'www.rapidvid.net', 'rapidvid.org', 'www.rapidvid.org'}
MAX_HTML = 4 * 1024 * 1024


def supported_page(url):
    if not isinstance(url,str) or len(url)>8192:return False
    try:
        p = urlsplit(url)
        return p.scheme == 'https' and p.hostname in PAGE_HOSTS and not p.username and not p.password and p.port in (None,443) and bool(re.fullmatch(r'/film/[a-zA-Z0-9_-]+/?',p.path))
    except (ValueError, TypeError):
        return False


def valid_embed(url):
    if not isinstance(url,str) or len(url)>8192:return False
    try:
        p = urlsplit(url)
        return p.scheme == 'https' and p.hostname in EMBED_HOSTS and not p.username and not p.password and p.port in (None,443) and bool(re.fullmatch(r'/(?:vod|vx|embed)/[a-zA-Z0-9_-]+/?',p.path))
    except (ValueError, TypeError):
        return False


def valid_stream(url):
    if not isinstance(url,str) or len(url)>8192:return False
    try:
        p = urlsplit(url)
        host=p.hostname or ''
        if p.scheme != 'https' or p.username or p.password or p.port not in (None,443):return False
        if not host or host.lower() in ('localhost','localhost.localdomain') or host.lower().endswith(('.local','.localhost','.internal')):return False
        try:return ipaddress.ip_address(host).is_global
        except ValueError:return '.' in host and not any(c.isspace() for c in url)
    except (ValueError, TypeError):
        return False


def page_details(html, url):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.find('h1') or soup.title
    poster = soup.find('meta',property='og:image')
    return {'title':title.get_text(' ',strip=True) if title else 'Video',
            'thumbnail':urljoin(url,poster.get('content','')) if poster else '',
            'embeds':[urljoin(url,t.get('data-src') or t.get('src','')) for t in soup.find_all('iframe')]}


def rapidvid_source(html):
    # Only recognize the observed player configuration; never eval site scripts.
    block = re.search(r'jwSetup\.sources\s*=\s*\[([\s\S]*?)\]\s*;',html)
    if not block:
        raise ValueError('Bu oynatıcının kaynak yapısı henüz desteklenmiyor.')
    encoded = re.search(r'[\'"]file[\'"]\s*:\s*av\(\s*[\'"]([A-Za-z0-9+/=]{1,16384})[\'"]\s*\)',block[1])
    direct = re.search(r'[\'"]file[\'"]\s*:\s*[\'"](https://[^\'"<>\s]+)',block[1])
    try:
        if encoded:
            data=base64.b64decode(encoded[1][::-1],validate=True).decode('latin1')
            text=''.join(chr(ord(c)-(ord('K9L'[i%3])%5+1)) for i,c in enumerate(data))
            stream=base64.b64decode(text,validate=True).decode('utf-8')
        elif direct:
            stream=direct[1]
        else:
            raise ValueError()
    except (ValueError,UnicodeError,binascii.Error):
        raise ValueError('Video kaynağı çözümlenemedi; oynatıcı yapısı değişmiş olabilir.')
    if not valid_stream(stream):
        raise ValueError('Oynatıcının kaynak sunucusu henüz desteklenmiyor.')
    return stream


class SiteResolver:
    extractor_key = 'FullHDFilmizlesene'
    def __init__(self, browser=site_browser, clock=time.monotonic):
        self.browser=browser
        self.clock=clock
        self.lock=threading.RLock()
        self.cache={}
        self.pages={}

    def _html(self, url, referer=None):
        # Never follow redirects to arbitrary hosts or read an unbounded response.
        headers={'User-Agent':requests.utils.default_user_agent()}
        if referer: headers['Referer']=referer
        for _ in range(4):
            if not (supported_page(url) or valid_embed(url)):
                raise ValueError('Desteklenmeyen sayfa yönlendirmesi.')
            with requests.get(url,headers=headers,timeout=(5,12),stream=True,allow_redirects=False) as response:
                if response.is_redirect:
                    url=urljoin(url,response.headers.get('Location',''))
                    continue
                response.raise_for_status()
                chunks=[];total=0
                for chunk in response.iter_content(65536):
                    total+=len(chunk)
                    if total>MAX_HTML:raise ValueError('Oynatıcı sayfası çok büyük.')
                    chunks.append(chunk)
                return b''.join(chunks).decode('utf-8',errors='replace')
        raise ValueError('Çok fazla sayfa yönlendirmesi.')

    def details(self, url, fresh=False):
        if not supported_page(url):raise ValueError('Bu site henüz desteklenmiyor.')
        with self.lock:
            entry=self.cache.get(url)
            if not fresh and entry and self.clock()-entry[0]<120:
                return dict(entry[1])
            saved=self.pages.get(url)
            if saved and self.clock()-saved[0]<180:
                data=saved[1]
            elif entry and fresh and entry[1].get('embed'):
                data=dict(entry[1],embeds=[entry[1]['embed']])
            else:
                try:
                    data=page_details(self._html(url),url)
                except requests.RequestException:
                    data={}
            embeds=list(dict.fromkeys(item for item in data.get('embeds',[]) if valid_embed(item)))[:4]
            if not embeds:
                data=self.browser.inspect(url)
                embeds=list(dict.fromkeys(item for item in data.get('embeds',[]) if valid_embed(item)))[:4]
            if not embeds:raise ValueError('Desteklenen Rapidvid oynatıcısı bulunamadı.')
            self.pages={key:value for key,value in self.pages.items() if self.clock()-value[0]<180}
            if len(self.pages)>=20:self.pages.pop(next(iter(self.pages)))
            self.pages[url]=(self.clock(),data)
            last_error=None
            for embed in embeds:
                headers={'Referer':urljoin(embed,'/'),'User-Agent':requests.utils.default_user_agent()}
                try:
                    streams=[]
                    try:
                        stream=rapidvid_source(self._html(embed,url))
                    except (ValueError,requests.RequestException):
                        observed=self.browser.inspect_player(embed,url)
                        streams=list(dict.fromkeys(source for source in observed.get('sources',[]) if valid_stream(source)))[:8]
                        stream=streams[0] if streams else None
                        if not stream:raise ValueError('Oynatıcıdan erişilebilir video kaynağı alınamadı.')
                        if observed.get('user_agent'):headers['User-Agent']=observed['user_agent']
                    break
                except ValueError as exc:
                    from services.site_browser import BrowserRequired
                    if isinstance(exc,BrowserRequired):raise
                    self.browser.close()
                    last_error=exc
            else:
                raise ValueError('Sayfadaki oynatıcılar çözümlenemedi. '+str(last_error or ''))
            result={'stream':stream,'streams':streams or [stream],'embed':embed,'headers':headers,
                    'title':str(data.get('title') or 'Video')[:500], 'thumbnail':str(data.get('thumbnail') or '')[:8192]}
            self.cache={key:value for key,value in self.cache.items() if self.clock()-value[0]<120}
            if len(self.cache)>=20:self.cache.pop(next(iter(self.cache)))
            self.cache[url]=(self.clock(),result)
            return dict(result)

    def extract(self, ydl, url, fresh=False):
        data=self.details(url,fresh=fresh)
        ydl.params['http_headers']=dict(ydl.params.get('http_headers') or {}, **data['headers'])
        streams=data.get('streams') or [data['stream']]
        def extract_source(stream):
            from services.generic_resolver import apply_source_context
            apply_source_context(ydl, stream, data.get('source_headers', {}).get(stream, data['headers']))
            return ydl.extract_info(stream,download=False)
        if len(streams)==1:
            info=extract_source(streams[0])
        else:
            previous=ydl.params.get('format')
            previous_selector=ydl.format_selector
            parts=[]
            try:
                ydl.params['format']='bestvideo+bestaudio/best'
                ydl.format_selector=ydl.build_format_selector('bestvideo+bestaudio/best')
                for stream in streams:
                    try:
                        part=extract_source(stream)
                        if part and not part.get('has_drm'):parts.append(part)
                    except Exception:
                        continue
            finally:
                ydl.format_selector=previous_selector
                if previous is None:ydl.params.pop('format',None)
                else:ydl.params['format']=previous
            if not parts:raise ValueError('Oynatıcının video kaynakları okunamadı.')
            info=dict(parts[0]);formats=[]
            for index,part in enumerate(parts):
                for item in part.get('formats') or [part]:
                    candidate=dict(item)
                    candidate['format_id']=str(index)+'-'+str(candidate.get('format_id') or 'source')
                    formats.append(candidate)
            info['formats']=formats
            # Select again from the combined source set with the user's requested quality.
            for key in ('requested_formats','requested_downloads','format_id','url','protocol','format','format_note','width','height','fps','vcodec','acodec'):
                info.pop(key,None)
        if not info or info.get('has_drm'):
            raise ValueError('Video kaynağı kullanılamıyor veya korumalı.')
        info.update(title=data['title'],webpage_url=url,original_url=url,
                    id=urlsplit(url).path.strip('/').split('/')[-1] or 'embedded-video',extractor_key=self.extractor_key)
        if len(streams)>1:
            info=ydl.process_ie_result(info,download=False)
        if data['thumbnail']:info['thumbnail']=data['thumbnail']
        info['http_headers']=dict(info.get('http_headers') or {}, **data['headers'])
        return info


site_resolver=SiteResolver()


def extract_media_info(ydl,url,fresh=False):
    from services.generic_resolver import generic_resolver, can_discover_after
    from services.site_browser import BrowserRequired
    from yt_dlp.utils import DownloadError, UnsupportedError
    if supported_page(url):
        try:
            return site_resolver.extract(ydl,url,fresh=fresh)
        except BrowserRequired:
            raise
        except (ValueError,requests.RequestException) as exc:
            if 'drm' in str(exc).lower():raise
            return generic_resolver.extract(ydl,url,fresh=fresh)
    if generic_resolver.pending(url):
        return generic_resolver.extract(ydl,url,fresh=fresh)
    try:
        return ydl.extract_info(url,download=False)
    except (DownloadError, UnsupportedError) as exc:
        if not can_discover_after(url,exc):raise
        return generic_resolver.extract(ydl,url,fresh=fresh)
