import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

def extract_video_url_from_page(page_url: str) -> str:
    """
    Sayfa URL'sinden gömülü video URL'sini tespit edip çıkarır.
    Adım 1: HTML çekme ve <video> / <meta> etiketlerini tarama.
    Adım 2: <iframe> ve regex ile fallback araması.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(page_url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.text
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 1. <video> etiketleri içinde src veya <source> araması
        video_tags = soup.find_all('video')
        for video in video_tags:
            # Doğrudan video etiketindeki src
            if video.has_attr('src'):
                return urljoin(page_url, video['src'])
            
            # İçindeki <source> etiketlerindeki src
            source_tags = video.find_all('source')
            for source in source_tags:
                if source.has_attr('src'):
                    return urljoin(page_url, source['src'])
        
        # 2. Open Graph meta etiketlerinde video araması
        # og:video veya og:video:url
        meta_video = soup.find('meta', property='og:video') or \
                     soup.find('meta', property='og:video:url') or \
                     soup.find('meta', attrs={'name': 'og:video'}) or \
                     soup.find('meta', attrs={'name': 'og:video:url'})
                     
        if meta_video and meta_video.has_attr('content'):
            return meta_video['content']

        # 3. <iframe> etiketleri içinde bilinen embed servislerini arama
        # (youtube.com/embed, player.vimeo.com, dailymotion.com/embed vb.)
        iframe_tags = soup.find_all('iframe')
        known_embed_domains = ['youtube.com/embed', 'player.vimeo.com', 'dailymotion.com/embed']
        for iframe in iframe_tags:
            if iframe.has_attr('src'):
                src = iframe['src']
                if any(domain in src for domain in known_embed_domains):
                    return urljoin(page_url, src)
                    
        # 4. Ham HTML içinde regex ile .mp4 / .m3u8 / .webm uzantılı URL arama
        # (script etiketleri, JSON bloklar dahil tüm html_content üzerinde)
        pattern = r'https?://[^\s"\'<>]+\.(?:mp4|m3u8|webm)(?:\?[^\s"\'<>]*)?'
        match = re.search(pattern, html_content)
        if match:
            return urljoin(page_url, match.group(0))
            
        # Eğer bu aşamalarda video bulunamazsa None dönüyoruz
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Sayfa çekilirken hata oluştu: {e}")
        # Hata fırlatmak yerine None dönüyoruz, böylece ana süreç sessizce patlamak 
        # yerine fallback mekanizmalarına veya ilgili hata mesajına (UX) yönelebilir.
        return None
