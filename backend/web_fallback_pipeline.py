"""Bounded discovery from search leads, with generic public HTTPS fetching."""
import logging
from urllib.parse import urlsplit
from web_product_search import discover_web_products, source_priority
from web_content_extractor import extract_web_content, rank_product_links
from secure_web_fetch import normalize_url
from web_product_validator import validate_discovery
logger = logging.getLogger(__name__)

def run_web_fallback(product_name):
    try:
        leads = discover_web_products(product_name, limit=12)
        result = {**leads, 'search_leads': leads.get('candidates', []), 'candidates': [], 'other_results': [], 'validation_status': 'not_started'}
        pages = {}; diagnostics = []; seen = set(); blocked = set()
        direct = []; roots = {}; attempts = 0
        for lead in result['search_leads'][:12]:
            try: url = normalize_url(lead['url'])
            except (ValueError, KeyError, UnicodeError): continue
            host = urlsplit(url).hostname
            root = 'https://' + host + '/'
            roots.setdefault(host, root)
            if url != root:
                direct.extend({**link, 'source_priority':source_priority(lead)} for link in rank_product_links(product_name, [{'url':url,'title':lead.get('title') or ''}], root))

        def attempt(link, homepage=False):
            nonlocal attempts
            url = link['url']; host = urlsplit(url).hostname
            if url in seen or host in blocked or attempts >= 6 or len(pages) >= 3:
                return []
            seen.add(url); attempts += 1
            page = extract_web_content(url, product_name if homepage else '')
            diagnostics.append({'url':url, **{k:page[k] for k in ('status','message','http_status','retry_after_seconds') if k in page}})
            if page.get('http_status') in (403, 429): blocked.add(host)
            if page.get('status') != 'success': return []
            if not homepage:
                pages[url] = {'candidate':link,'content':page}
            return page.get('ranked_product_links', [])

        # Try direct leads first, spreading the initial attempts across hosts.
        direct.sort(key=lambda x: (x['source_priority'], -x['match_score']))
        for priority in (0, 1, 2):
            first = []; rest = []; hosts = set()
            for link in direct:
                if link['source_priority'] != priority: continue
                host = urlsplit(link['url']).hostname
                (rest if host in hosts else first).append(link)
                hosts.add(host)
            for link in first + rest:
                attempt(link)
        # Homepage discovery remains useful for brand-only search leads.
        for host, root in list(roots.items())[:2]:
            if attempts >= 6 or len(pages) >= 3: break
            for link in attempt({'url':root}, homepage=True):
                attempt(link)
        result['extraction_diagnostics']=diagnostics
        if not pages:
            result['validation_status']='no_extractable_pages'; return result
        validated=validate_discovery({'status':'success','search_query':product_name,'product_pages':list(pages.values())})
        result.update(candidates=validated.get('candidates',[]),other_results=validated.get('other_results',[]),validation_status=validated['status'])
        result['candidates'].sort(key=lambda c:len(c.get('facts',[])),reverse=True)
        return result
    except Exception:
        logger.exception('Web fallback failed')
        return {'status':'unavailable','validation_status':'unavailable','candidates':[],'search_leads':[],'other_results':[]}
