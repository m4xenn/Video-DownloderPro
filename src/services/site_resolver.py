"""Initial FullHDFilmizlesene/Rapidvid adapter. No remote JavaScript evaluation."""
import base64
import binascii
import re
import threading
import time
from urllib.parse import urlsplit, urljoin

import requests
from bs4 import BeautifulSoup
from services.site_browser import site_browser

PAGE_HOSTS = {'fullhdfilmizlesene.now', 'www.fullhdfilmizlesene.now'}
EMBED_HOSTS = {'rapidvid.net', 'www.rapidvid.net'}
MAX_HTML = 4 * 1024 * 1024


def supported_page(url):
    try:
        p = urlsplit(url)
        return p.scheme == 'https' and p.hostname in PAGE_HOSTS and not p.username and not p.password and p.port in (None,443) and bool(re.fullmatch(r'/film/[a-zA-Z0-9_-]+/?',p.path))
    except (ValueError, TypeError):
        return False


def valid_embed(url):
    try:
        p = urlsplit(url)
        return p.scheme == 'https' and p.hostname in EMBED_HOSTS and not p.username and not p.password and p.port in (None,443) and bool(re.fullmatch(r'/vod/[a-zA-Z0-9_-]+/?',p.path))
    except (ValueError, TypeError):
        return False


def valid_stream(url):
    try:
        p = urlsplit(url)
        return p.scheme == 'https' and not p.username and not p.password and p.port in (None,443) and bool(re.fullmatch(r'(?:s[0-9]+\.)?cdnimages[0-9]+\.(?:shop|store|com|net|org)',p.hostname or ''))
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
    def __init__(self, browser=site_browser, clock=time.monotonic):
        self.browser=browser
        self.clock=clock
        self.lock=threading.RLock()
        self.cache={}

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
            if entry and fresh and entry[1].get('embed'):
                data=dict(entry[1],embeds=[entry[1]['embed']])
            else:
                try:
                    data=page_details(self._html(url),url)
                except requests.RequestException:
                    data={}
            embeds=[item for item in data.get('embeds',[]) if valid_embed(item)]
            if not embeds:
                data=self.browser.inspect(url)
                embeds=[item for item in data.get('embeds',[]) if valid_embed(item)]
            if not embeds:raise ValueError('Desteklenen Rapidvid oynatıcısı bulunamadı.')
            embed=embeds[0]
            try:
                stream=rapidvid_source(self._html(embed,url))
            except requests.HTTPError as exc:
                raise ValueError('Oynatıcıya erişilemedi; video kaldırılmış veya erişim engellenmiş olabilir.') from exc
            result={'stream':stream,'embed':embed,'headers':{'Referer':'https://rapidvid.net/','User-Agent':requests.utils.default_user_agent()},
                    'title':str(data.get('title') or 'Video')[:500], 'thumbnail':str(data.get('thumbnail') or '')[:8192]}
            self.cache={key:value for key,value in self.cache.items() if self.clock()-value[0]<120}
            if len(self.cache)>=20:self.cache.pop(next(iter(self.cache)))
            self.cache[url]=(self.clock(),result)
            return dict(result)

    def extract(self, ydl, url, fresh=False):
        data=self.details(url,fresh=fresh)
        ydl.params['http_headers']=dict(ydl.params.get('http_headers') or {}, **data['headers'])
        info=ydl.extract_info(data['stream'],download=False)
        if not info or info.get('has_drm'):
            raise ValueError('Video kaynağı kullanılamıyor veya korumalı.')
        info.update(title=data['title'],webpage_url=url,original_url=url,
                    id=urlsplit(url).path.strip('/').split('/')[-1],extractor_key='FullHDFilmizlesene')
        if data['thumbnail']:info['thumbnail']=data['thumbnail']
        info['http_headers']=dict(info.get('http_headers') or {}, **data['headers'])
        return info


site_resolver=SiteResolver()


def extract_media_info(ydl,url,fresh=False):
    if supported_page(url):return site_resolver.extract(ydl,url,fresh=fresh)
    return ydl.extract_info(url,download=False)
