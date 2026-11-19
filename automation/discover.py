
import json
import os
import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_PUBLISHABLE_KEY"]
EMAIL = os.environ["SUPABASE_EMAIL"]
PASSWORD = os.environ["SUPABASE_PASSWORD"]

USER_AGENT = "DramaLibraryBot/1.0"

KNOWN_PLATFORMS = [
    "Vigloo",
    "GoodShort",
    "FlickReels",
    "StoreEl",
    "ToonShort",
    "KalosTV",
    "ReelShort",
    "DramaBox",
    "ShortMax",
    "NetShort",
    "DramaWave",
    "FlexTV",
    "ReadShort",
    "SnackShort",
    "StoryReel",
    "MoboReels",
    "JoyReels",
    "Sereal+",
    "PineDrama",
    "FreeReels",
    "Melolo",
    "RapidTV",
    "FlareFlow",
    "Playlet",
    "DreameShort",
    "ShortTV",
    "RivoShort"
]


def request_json(url, method="GET", data=None, token=None):
    headers = {
        "apikey": SUPABASE_KEY,
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token or SUPABASE_KEY}"
    }

    body = json.dumps(data).encode() if data is not None else None

    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method=method
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())


def get_page(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT}
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode(
            "utf-8",
            errors="replace"
        )


class PageParser(HTMLParser):

    def __init__(self):
        super().__init__()
        self.links = []
        self.text = []
        self.current_link = None
        self.link_text = []
        self.in_h1 = False
        self.h1_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "a" and attrs.get("href"):
            self.current_link = attrs["href"]
            self.link_text = []

        if tag == "h1":
            self.in_h1 = True
            self.h1_text = []

    def handle_data(self, data):
        clean = data.strip()

        if clean:
            self.text.append(clean)

        if self.current_link is not None:
            self.link_text.append(data)

        if self.in_h1:
            self.h1_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current_link is not None:
            label = " ".join(
                " ".join(self.link_text).split()
            )

            self.links.append((self.current_link, label))
            self.current_link = None
            self.link_text = []

        if tag == "h1":
            self.in_h1 = False


def extract_drama_links(html, base_url):
    parser = PageParser()
    parser.feed(html)

    found = {}

    for href, label in parser.links:
        full_url = urljoin(base_url, href)
        path = urlparse(full_url).path

        if path.startswith("/series/") and label:
            found[full_url] = label

    return found


def inspect_drama(url):
    html = get_page(url)

    parser = PageParser()
    parser.feed(html)

    page_text = " ".join(parser.text)

    title = " ".join(
        " ".join(parser.h1_text).split()
    )

    if not title:
        title = "Title not detected"

    description = ""

    match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)',
        html,
        re.I
    )

    if match:
        description = match.group(1).strip()

    episode_match = re.search(
        r'(?:Episodes\s+(\d+)|(\d+)\s+Episodes)',
        page_text,
        re.I
    )

    if episode_match:
        episodes = (
            episode_match.group(1)
            or episode_match.group(2)
        )
    else:
        episodes = "Not detected"

    original_platform = "Not detected"

    for platform in KNOWN_PLATFORMS:
        pattern = (
            r"(?<![A-Za-z])"
            + re.escape(platform)
            + r"(?![A-Za-z])"
        )

        if re.search(pattern, page_text, re.I):
            original_platform = platform
            break

    return {
        "title": title,
        "synopsis": description,
        "episodes": episodes,
        "original_platform": original_platform,
        "watch_page": url
    }


def main():

    login = request_json(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        method="POST",
        data={
            "email": EMAIL,
            "password": PASSWORD
        }
    )

    token = login["access_token"]

    print("Database login successful.")

    sources = request_json(
        f"{SUPABASE_URL}/rest/v1/source_sites"
        "?select=name,website_url"
        "&active=eq.true"
        "&name=eq.DramaExpress",
        token=token
    )

    if not sources or not sources[0].get("website_url"):
        print("DramaExpress URL not found in source directory.")
        return

    source_name = sources[0]["name"]
    home_url = sources[0]["website_url"]

    print(f"Checking {source_name}: {home_url}")

    html = get_page(home_url)

    dramas = extract_drama_links(html, home_url)

    print(
        f"Found {len(dramas)} drama links on the homepage."
    )

    for index, url in enumerate(
        list(dramas.keys())[:10],
        start=1
    ):

        try:
            drama = inspect_drama(url)

            print(f"\nDRAMA {index}")

            print(
                json.dumps(
                    drama,
                    ensure_ascii=False,
                    indent=2
                )
            )

        except Exception as error:
            print(
                f"\nCould not inspect {url}: {error}"
            )

    print(
        "\nDiscovery test finished. "
        "No database records were changed."
    )


if __name__ == "__main__":
    main()

