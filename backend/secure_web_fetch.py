"""HTTPS fetch with DNS pinning and certificate verification; no proxy or cookies."""
import http.client
import ipaddress
import re
import socket
import ssl
import time
import threading
from collections import OrderedDict
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from urllib.parse import urlsplit, urljoin, urlunsplit

MAX_BYTES = 2_000_000

def normalize_url(url):
    if not isinstance(url, str) or len(url)>4096 or re.search(r'[\x00-\x20\x7f\\]', url):
        raise ValueError('Invalid URL')
    p = urlsplit(url)
    if p.scheme != 'https' or p.username is not None or p.password is not None or p.port not in (None,443) or not p.hostname:
        raise ValueError('Only public HTTPS URLs are supported')
    host = p.hostname.rstrip('.').encode('idna').decode('ascii').lower()
    if not re.fullmatch(r'[a-z0-9.-]+',host) or '.' not in host or host.endswith(('.localhost','.local','.internal','.home.arpa')):
        raise ValueError('Invalid public hostname')
    try: ipaddress.ip_address(host)
    except ValueError: pass
    else: raise ValueError('IP literal URLs are blocked')
    return urlunsplit(('https',host,p.path or '/',p.query,''))

def public_addresses(host):
    addresses = list(dict.fromkeys(x[4][0] for x in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)))
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global or ip.is_multicast or ip.is_reserved or getattr(ip,'ipv4_mapped',None) or getattr(ip,'sixtofour',None) or getattr(ip,'teredo',None) or ip in ipaddress.ip_network('64:ff9b::/96') or ip in ipaddress.ip_network('64:ff9b:1::/48'):
            raise ValueError('Non-public or special-use address blocked')
    if not addresses: raise ValueError('No public address')
    return addresses

class PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self,host,address,timeout):
        super().__init__(host,443,timeout=timeout,context=ssl.create_default_context())
        self.address = address
    def connect(self):
        raw = socket.create_connection((self.address,443),self.timeout)
        try: self.sock = self._context.wrap_socket(raw,server_hostname=self.host)
        except Exception:
            raw.close(); raise

_lock = threading.Lock()
_cache = OrderedDict()
_cooldowns = {}
CACHE_TTL = 600

class WebsiteHTTPError(ValueError):
    def __init__(self, status, retry_after=None):
        self.status = status
        self.retry_after = retry_after
        super().__init__(f"Website HTTP {status}")


def cooldown_seconds(header):
    try:
        return max(60, int(header))
    except (TypeError, ValueError):
        try:
            return max(60, int((parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()) + 1)
        except (TypeError, ValueError, OverflowError):
            return 300


def fetch_html(url):
    key = normalize_url(url)
    with _lock:
        entry = _cache.get(key)
        if entry and entry[0] > time.monotonic():
            _cache.move_to_end(key)
            return entry[1]
    result = _fetch_html(key)
    with _lock:
        _cache[key] = (time.monotonic() + CACHE_TTL, result)
        _cache.move_to_end(key)
        while len(_cache) > 16:
            _cache.popitem(last=False)
    return result


def _fetch_html(url):
    deadline = time.monotonic()+30
    for hop in range(4):
        url = normalize_url(url)
        p = urlsplit(url)
        with _lock:
            now = time.monotonic()
            for host in list(_cooldowns):
                if _cooldowns[host] <= now:
                    del _cooldowns[host]
            until = _cooldowns.get(p.hostname, 0)
            if until > now:
                raise WebsiteHTTPError(429, int(until - now) + 1)
        addresses = public_addresses(p.hostname)
        remaining = deadline-time.monotonic()
        if remaining<=0: raise TimeoutError('Fetch deadline exceeded')
        conn = PinnedHTTPS(p.hostname,addresses[0],min(8,remaining))
        try:
            conn.request('GET',p.path+('?' + p.query if p.query else ''),headers={'User-Agent':'NutriLensAI/0.1','Accept':'text/html,application/xhtml+xml','Accept-Encoding':'identity','Connection':'close'})
            response = conn.getresponse()
            if response.status in (301,302,303,307,308):
                location = response.getheader('Location')
                if not location: raise ValueError('Missing redirect location')
                url = urljoin(url,location); continue
            if response.status != 200:
                delay = None
                if response.status == 429:
                    delay = cooldown_seconds(response.getheader('Retry-After'))
                    with _lock:
                        _cooldowns[p.hostname] = max(_cooldowns.get(p.hostname, 0), time.monotonic() + delay)
                raise WebsiteHTTPError(response.status, delay)
            if response.getheader('Content-Type','').split(';')[0].strip().lower() not in ('text/html','application/xhtml+xml'): raise ValueError('Expected HTML')
            if response.getheader('Content-Encoding','identity').lower() != 'identity': raise ValueError('Unsupported content encoding')
            data = bytearray()
            while True:
                if time.monotonic()>deadline: raise TimeoutError('Fetch deadline exceeded')
                chunk = response.read1(16384)
                if not chunk: break
                data.extend(chunk)
                if len(data)>MAX_BYTES: raise ValueError('Page exceeds size limit')
            return url,bytes(data)
        finally: conn.close()
    raise ValueError('Too many redirects')
