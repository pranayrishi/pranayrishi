"""Refresh the "Latest writing" and "Latest videos" lists in README.md.

Runs daily from .github/workflows/build.yml. Uses only the standard library.
If a feed can't be reached, that section is left as it was.
"""
import html
import pathlib
import re
import urllib.request
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).parent
README = ROOT / "README.md"
MEDIUM_FEED = "https://medium.com/feed/@pranayrishi.nalem"
YOUTUBE_HANDLE = "https://www.youtube.com/@programmingwithrishinalem"
UA = {"User-Agent": "Mozilla/5.0 (profile-readme-bot)"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def replace_block(text, marker, lines):
    pattern = re.compile(rf"(<!-- {marker} starts -->\n).*?(\n<!-- {marker} ends -->)", re.S)
    return pattern.sub(lambda m: m.group(1) + "\n".join(lines) + m.group(2), text)


def clean(title):
    return html.unescape(title).replace("[", "(").replace("]", ")").strip()


def medium_posts(limit=5):
    root = ET.fromstring(fetch(MEDIUM_FEED))
    items = []
    for item in root.iter("item"):
        title, link = item.findtext("title"), item.findtext("link")
        if title and link:
            items.append(f"- [{clean(title)}]({link.split('?')[0]})")
        if len(items) == limit:
            break
    return items


def youtube_videos(limit=4):
    page = fetch(YOUTUBE_HANDLE).decode("utf-8", "ignore")
    m = re.search(r'"(?:channelId|externalId)":"(UC[\w-]{22})"', page)
    if not m:
        return []
    feed = fetch(f"https://www.youtube.com/feeds/videos.xml?channel_id={m.group(1)}")
    ns = {"a": "http://www.w3.org/2005/Atom"}
    items = []
    for entry in ET.fromstring(feed).findall("a:entry", ns)[:limit]:
        title = entry.findtext("a:title", namespaces=ns)
        link = entry.find("a:link", ns).get("href")
        items.append(f"- [{clean(title)}]({link})")
    return items


def main():
    text = README.read_text()
    for marker, source, more in (
        ("medium", medium_posts, "- [All posts on Medium](https://medium.com/@pranayrishi.nalem)"),
        ("youtube", youtube_videos, f"- [All videos on YouTube]({YOUTUBE_HANDLE})"),
    ):
        try:
            lines = source()
        except Exception as exc:  # keep the old list if a feed is down
            print(f"{marker}: skipped ({exc})")
            continue
        if lines:
            text = replace_block(text, marker, lines + [more])
            print(f"{marker}: {len(lines)} items")
    README.write_text(text)


if __name__ == "__main__":
    main()
