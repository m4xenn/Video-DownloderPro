"""Shared boundaries for untrusted links and the local application API."""
import ipaddress
import socket
from urllib.parse import urlsplit


class UnsafeLink(ValueError):
    code = 'unsafe_link'

    def __init__(self):
        super().__init__('Unsafe link or network destination.')


def global_address(value):
    address=ipaddress.ip_address(value)
    return address.is_global and not address.is_multicast and not address.is_reserved


def public_link(url, resolve=False):
    if not isinstance(url, str) or not 1 <= len(url) <= 8192:
        return False
    if any(ord(c) < 33 or ord(c) == 127 for c in url) or '\\' in url:
        return False
    try:
        parsed=urlsplit(url)
        host=(parsed.hostname or '').lower().rstrip('.')
        if parsed.scheme not in ('https','http') or not host or parsed.username is not None or parsed.password is not None:
            return False
        # Validate ports, including malformed and out-of-range values.
        port=parsed.port or (443 if parsed.scheme=='https' else 80)
        if not 1 <= port <= 65535 or '%' in host:
            return False
        if host=='localhost' or host.endswith(('.localhost','.local','.internal','.home','.lan')):
            return False
        try:
            address=ipaddress.ip_address(host)
        except ValueError:
            # getaddrinfo also canonicalizes numeric aliases such as 127.1,
            # 2130706433 and 0x7f000001; do not treat them as public DNS names.
            try:
                numeric=socket.inet_aton(host)
            except OSError:
                numeric=None
            if numeric is not None:
                return global_address(numeric)
            if '.' not in host or any(not label for label in host.split('.')):
                return False
            host.encode('idna')
        else:
            if not global_address(address) or getattr(address,'ipv4_mapped',None) and not global_address(address.ipv4_mapped):
                return False
        if resolve:
            addresses=socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)
            return bool(addresses) and all(global_address(item[4][0]) for item in addresses)
        return True
    except (ValueError,TypeError,OSError,UnicodeError):
        return False


def require_public_link(url, resolve=False):
    if not public_link(url,resolve):
        raise UnsafeLink()
    return url


def local_request_allowed(request):
    """Reject browser-origin attacks, including DNS rebinding and null origins.

    Header-less native clients remain supported. Browser clients cannot forge
    Host/Origin/Sec-Fetch-Site. Never expose a CORS allow-origin response.
    """
    try:
        host=urlsplit(request.host_url).hostname
        if host not in ('127.0.0.1','localhost','::1'):
            return False
        if request.headers.get('Sec-Fetch-Site') in ('cross-site','same-site'):
            return False
        origin=request.headers.get('Origin')
        if origin is not None and origin != request.host_url.rstrip('/'):
            return False
        referer=request.headers.get('Referer')
        if referer:
            parsed=urlsplit(referer)
            if f'{parsed.scheme}://{parsed.netloc}' != request.host_url.rstrip('/'):
                return False
        return True
    except (ValueError,TypeError):
        return False
