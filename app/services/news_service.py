import httpx
import re
import xml.etree.ElementTree as ET
from cachetools import TTLCache

cache = TTLCache(maxsize=50, ttl=600)
http_client = httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"})


RSS_FEEDS = [
    "https://cointelegraph.com/rss",
    "https://cryptonews.com/news/feed/",
    "https://bitcoinmagazine.com/.rss/full/",
    "https://.coindesk.com/arc/outboundfeeds/rss/",
]


class NewsService:

    async def get_crypto_news(self, limit: int = 10, source: str = "all") -> dict:
        key = f"news_{limit}_{source}"
        if key in cache:
            return cache[key]

        feeds = RSS_FEEDS if source == "all" else [source]
        articles = []

        for feed_url in feeds:
            try:
                resp = await http_client.get(feed_url)
                resp.raise_for_status()
                root = ET.fromstring(resp.text)

                ns = {"media": "http://search.yahoo.com/mrss/"}
                items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")

                for item in items[:limit]:
                    title = self._get_text(item, "title")
                    link = self._get_text(item, "link")
                    if link is None:
                        link_el = item.find("{http://www.w3.org/2005/Atom}link")
                        link = link_el.get("href", "") if link_el is not None else ""
                    pub_date = self._get_text(item, "pubDate") or self._get_text(item, "published") or self._get_text(item, "updated")
                    description = self._get_text(item, "description") or self._get_text(item, "{http://www.w3.org/2005/Atom}summary") or ""
                    description = self._clean_html(description)[:300]

                    image = ""
                    media_thumb = item.find("media:thumbnail", ns)
                    media_content = item.find("media:content", ns)
                    enclosure = item.find("enclosure")
                    if media_thumb is not None:
                        image = media_thumb.get("url", "")
                    elif media_content is not None:
                        image = media_content.get("url", "")
                    elif enclosure is not None and "image" in enclosure.get("type", ""):
                        image = enclosure.get("url", "")

                    if title:
                        articles.append({
                            "title": title,
                            "url": link or "",
                            "published": pub_date or "",
                            "description": description,
                            "image": image,
                            "source": self._extract_source(feed_url),
                        })
            except Exception:
                continue

        seen = set()
        unique = []
        for a in articles:
            if a["title"] not in seen:
                seen.add(a["title"])
                unique.append(a)

        result = {
            "articles": unique[:limit],
            "total": len(unique),
        }
        cache[key] = result
        return result

    @staticmethod
    def _get_text(item, tag: str) -> str | None:
        el = item.find(tag)
        return el.text.strip() if el is not None and el.text else None

    @staticmethod
    def _clean_html(html: str) -> str:
        clean = re.sub(r"<[^>]+>", "", html)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    @staticmethod
    def _extract_source(url: str) -> str:
        if "cointelegraph" in url:
            return "CoinTelegraph"
        if "cryptonews" in url:
            return "CryptoNews"
        if "bitcoinmagazine" in url:
            return "Bitcoin Magazine"
        if "coindesk" in url:
            return "CoinDesk"
        return url.split("/")[2]


news_service = NewsService()
