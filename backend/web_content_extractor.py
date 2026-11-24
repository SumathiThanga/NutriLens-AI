"""Bounded webpage extraction for local NutriLens development.
Public HTTPS only, with pinned DNS addresses. Bounded discovery.
"""
import json
import os
import re
from urllib.parse import urlsplit, urljoin, unquote, urlunsplit
import http.client
from secure_web_fetch import normalize_url, fetch_html, WebsiteHTTPError
from bs4 import BeautifulSoup

MAX_BYTES = 2_000_000

def _tokens(value):
    return set(re.findall(r"[a-z0-9]+", unquote(value).casefold())) - {
        "product", "products", "pack", "packs", "buy", "online", "the", "and", "of"
    }


def rank_product_links(product_name, links, source_url):
    requested = _tokens(product_name)
    host = urlsplit(source_url).hostname or ""
    requested -= _tokens(host.split(".")[-2] if "." in host else host)
    if not requested:
        return []
    ranked = []
    for link in links:
        words = _tokens(link["title"] + " " + urlsplit(link["url"]).path)
        overlap = requested & words
        if len(overlap) < min(2, len(requested)):
            continue
        score = len(overlap) / len(requested)
        if score < 0.5:
            continue
        ranked.append({**link, "match_score": round(score, 3),
                       "matched_terms": sorted(overlap), "verification_status": "unverified"})
    return sorted(ranked, key=lambda x: (-x["match_score"], x["url"]))


def extract_web_content(url: str, product_name: str = "") -> dict:
    try:
        url, data = fetch_html(url)
        def permitted(value):
            try:
                return urlsplit(normalize_url(value)).hostname == urlsplit(url).hostname
            except (ValueError, UnicodeError):
                return False
        soup = BeautifulSoup(bytes(data), 'html.parser')
        products = []
        def visit(node):
            if isinstance(node, list):
                for item in node: visit(item)
            elif isinstance(node, dict):
                types = node.get('@type', [])
                if isinstance(types, str): types = [types]
                if isinstance(types, list) and 'Product' in types:
                    products.append({k:node[k] for k in ('name','brand','description','sku','gtin','gtin8','gtin12','gtin13','gtin14','nutrition','image') if k in node})
                for value in node.values():
                    if isinstance(value,(dict,list)): visit(value)
        for script in soup.find_all('script', type='application/ld+json'):
            try: visit(json.loads(script.get_text()))
            except (ValueError, RecursionError): continue
        title = soup.title.get_text(strip=True) if soup.title else ''
        meta = soup.find('meta', attrs={'name':'description'})
        links = {}
        for a in soup.find_all('a', href=True):
            target = urljoin(url,a['href']).split('#')[0]
            if permitted(target) and urlsplit(target).path not in ('', '/'):
                p = urlsplit(target)
                target = urlunsplit((p.scheme, p.netloc, p.path, '', ''))
                label = a.get_text(' ', strip=True)[:200]
                if not label:
                    img = a.find('img')
                    label = str(img.get('alt', ''))[:200] if img else ''
                if len(label) > len(links.get(target, '')) or target not in links:
                    links[target] = label
        for tag in soup(['script','style','nav','footer','header','noscript']): tag.decompose()
        all_links = [{'url':k,'title':v} for k,v in links.items()]
        ranked = rank_product_links(product_name, all_links, url) if product_name else []
        return {'status':'success','source_url':url,'verification_status':'unverified','title':title,'description':meta.get('content','') if meta else '', 'structured_products':products[:20], 'page_text':soup.get_text(' ',strip=True)[:20000], 'product_links':all_links[:50], 'total_product_links':len(all_links), 'ranked_product_links':ranked[:10]}
    except WebsiteHTTPError as exc:
        return {'status':'unavailable','source_url':url,'message':str(exc),
                'http_status':exc.status,'retry_after_seconds':exc.retry_after,
                'verification_status':'unverified'}
    except (OSError, http.client.HTTPException, ValueError, KeyError) as exc:
        return {'status':'unavailable','source_url':url,'message':str(exc),'verification_status':'unverified'}

def discover_product_pages(url: str, product_name: str, limit: int = 3) -> dict:
    homepage = extract_web_content(url, product_name)
    if homepage.get("status") != "success":
        return homepage
    ranked = homepage["ranked_product_links"]
    pages = []
    for link in ranked[:max(0, min(limit, 3))]:
        page = extract_web_content(link["url"])
        pages.append({"candidate": link, "content": page})
    return {"status": "success", "source_url": homepage["source_url"],
            "search_query": product_name, "total_product_links": homepage["total_product_links"],
            "ranked_product_links": ranked, "product_pages": pages,
            "verification_status": "unverified"}


if __name__ == '__main__':
    import argparse
    from dotenv import load_dotenv
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs='?', default='https://kruncho.com/')
    parser.add_argument('product_name', nargs='?', default='')
    args = parser.parse_args()
    result = (discover_product_pages(args.url, args.product_name) if args.product_name
              else extract_web_content(args.url))
    print(json.dumps(result, indent=2, ensure_ascii=True))
