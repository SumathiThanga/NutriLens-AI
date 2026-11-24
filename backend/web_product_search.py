"""Brave web discovery: unverified product leads, never nutrition records."""
import html
import logging
import os
import re
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)
BRAVE_ENDPOINT = 'https://api.search.brave.com/res/v1/web/search'
STOP = {'pack','packet','packs','g','gm','grams','kg','ml',
        'food','foods','the','and','of','with','new','nutrition','ingredients'}
GENERIC = {'cookie','biscuit','millet','snack','chips','flakes','mix','chocolate','milk'}


def _tokens(text):
    words = re.findall(r'[a-z0-9]+', text.casefold())
    return [w[:-1] if len(w)>4 and w.endswith('s') and not w.endswith('ss') else w
            for w in words if w not in STOP and not w.isdigit()]


def _clean(value):
    return html.unescape(re.sub(r'<[^>]*>', '', str(value or ''))).strip()


def _queries(name):
    words = name.split()
    simplified = ' '.join(w for w in words if w.casefold() not in STOP)
    options = [name, simplified, ' '.join(words[:2]),
               ' '.join([words[0], *words[-2:]]) if len(words)>2 else name]
    return list(dict.fromkeys(q for q in options if len(q)>1))[:4]


def source_priority(candidate):
    """Heuristic only: product listings before reviews and homepages."""
    parsed = urlparse(candidate['url'])
    path = parsed.path.lower()
    if any(x in path for x in ('/reviews/', '/review/', '/blog/', '/blogs/')):
        return 2
    if path in ('', '/'):
        return 1
    return 0


def diverse_candidates(candidates):
    ordered = sorted(candidates, key=lambda c: (source_priority(c), -c['match_score']))
    result = []
    for priority in (0, 1, 2):
        seen = set(); repeat = []
        for candidate in ordered:
            if source_priority(candidate) != priority:
                continue
            host = candidate['domain'].lower().removeprefix('www.')
            if host in seen:
                repeat.append(candidate)
            else:
                result.append(candidate); seen.add(host)
        result.extend(repeat)
    return result


def discover_web_products(product_name: str, limit: int = 12) -> dict:
    api_key = os.getenv('BRAVE_SEARCH_API_KEY', '').strip()
    if not api_key:
        return {'status':'not_configured','candidates':[], 'message':'Set BRAVE_SEARCH_API_KEY.'}
    name = ' '.join(product_name.split())[:160]
    requested = set(_tokens(name))
    if len(name)<2 or not requested:
        return {'status':'invalid_query','candidates':[], 'message':'Enter a product name.'}
    distinctive = requested - GENERIC
    limit = max(1, min(limit, 15))
    candidates, seen, diagnostics = [], set(), []
    successful = 0
    for query in _queries(name):
        logger.debug('Brave query: %s', query)
        try:
            response = requests.get(BRAVE_ENDPOINT,
                headers={'Accept':'application/json','X-Subscription-Token':api_key},
                params={'q':query,'count':15,'search_lang':'en','country':'IN'},
                timeout=(5,12))
            response.raise_for_status()
            payload = response.json()
            results = payload.get('web', {}).get('results', [])
            if not isinstance(results, list):
                raise ValueError('Unexpected results format')
        except (requests.RequestException, ValueError, AttributeError) as exc:
            status = getattr(getattr(exc, 'response', None), 'status_code', None)
            logger.warning('Brave search failed: %s (HTTP %s)', type(exc).__name__, status)
            diagnostics.append({'query':query,'status':'unavailable','http_status':status})
            if status in (401,403,429):
                break
            continue
        successful += 1
        accepted = rejected = duplicates = 0
        logger.debug('Brave raw results: %s', len(results))
        for item in results:
            if not isinstance(item, dict):
                rejected += 1
                continue
            title = _clean(item.get('title'))[:240]
            snippet = _clean(item.get('description'))[:500]
            url = str(item.get('url') or '')
            # Avoid logging external page content.
            try:
                parsed = urlparse(url)
                valid = parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password
            except ValueError:
                valid = False
            combined = set(_tokens(title + ' ' + snippet))
            overlap = requested & combined
            if (not valid or len(overlap)<min(2,len(requested))
                or (distinctive and not distinctive & overlap)
                or not (requested & set(_tokens(title)))
                or len(overlap)/len(requested)<0.5):
                rejected += 1
                continue
            if url in seen:
                duplicates += 1
                continue
            seen.add(url)
            accepted += 1
            candidates.append({'title':title,'url':url,'domain':parsed.hostname,
                'snippet':snippet,'source_type':'web_search','verification_status':'unverified',
                'nutrition_per_100g':None,'match_score':round(len(overlap)/len(requested),3)})
        diagnostics.append({'query':query,'status':'success','raw_results':len(results),
                            'accepted':accepted,'rejected':rejected,'duplicates':duplicates})
        logger.debug('Brave accepted=%s rejected=%s duplicates=%s', accepted, rejected, duplicates)
        if len(candidates)>=limit and len({c['domain'].removeprefix('www.') for c in candidates if source_priority(c)==0})>=5:
            break
    candidates = diverse_candidates(candidates)
    raw_count = sum(d.get('raw_results',0) for d in diagnostics)
    reason = ('candidates_found' if candidates else 'search_unavailable' if not successful
              else 'filtered_out' if raw_count else 'no_raw_results')
    return {'status':'success' if successful else 'unavailable','candidates':candidates[:limit],
            'reason':reason,'diagnostics':diagnostics,
            'message':'Web pages are unverified leads; check the exact product and label.'}
