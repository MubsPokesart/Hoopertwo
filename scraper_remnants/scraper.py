"""
Basketball Reference Player Image Scraper

Minimal, modular script to scrape player images from Basketball Reference.

Note: Basketball Reference may block automated requests. For production use,
consider using a service like ScraperAPI or fetching HTML manually.
"""

import requests
from bs4 import BeautifulSoup
from typing import Optional
import time


def get_player_url(player_name: str) -> str:
    """
    Convert player name to Basketball Reference URL format.

    Basketball Reference URLs follow pattern:
    /players/{first_letter}/{last_name_first5}{first_name_first2}{suffix}.html

    Args:
        player_name: Full name of player (e.g., "Brook Lopez")

    Returns:
        Full URL to player's page
    """
    # This is a simplified version - in practice, you'd need to handle
    # name variations and suffixes (01, 02, etc.) for players with same names
    parts = player_name.lower().split()
    if len(parts) < 2:
        raise ValueError("Player name must include first and last name")

    first_name = parts[0]
    last_name = parts[-1]

    # Basketball Reference naming convention
    first_letter = last_name[0]
    last_5 = last_name[:5]
    first_2 = first_name[:2]
    suffix = "01"  # Default suffix

    player_id = f"{last_5}{first_2}{suffix}"
    url = f"https://www.basketball-reference.com/players/{first_letter}/{player_id}.html"

    return url


def parse_player_image_from_html(html_content: str) -> Optional[str]:
    """
    Parse player image URL from Basketball Reference HTML.

    Args:
        html_content: HTML content of player page

    Returns:
        Image URL if found, None otherwise
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Find div with id="meta"
    meta_div = soup.find('div', id='meta')
    if not meta_div:
        return None

    # Find div with class="media-item" inside meta
    media_item = meta_div.find('div', class_='media-item')
    if not media_item:
        return None

    # Find img tag inside media-item
    img = media_item.find('img')
    if not img:
        return None

    # Extract src attribute
    img_url = img.get('src')
    return img_url


def scrape_player_image(url: str, use_session: bool = True, delay: float = 1.0) -> Optional[str]:
    """
    Scrape player image URL from Basketball Reference page.

    Args:
        url: Basketball Reference player page URL
        use_session: Whether to use a session (helps avoid blocks)
        delay: Delay before request to avoid rate limiting (seconds)

    Returns:
        Image URL if found, None otherwise
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.basketball-reference.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin'
    }

    # Delay to avoid rate limiting
    if delay > 0:
        time.sleep(delay)

    try:
        if use_session:
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=10)
        else:
            response = requests.get(url, headers=headers, timeout=10)

        response.raise_for_status()
        return parse_player_image_from_html(response.text)

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def get_player_image(player_name: str, player_id: Optional[str] = None) -> Optional[str]:
    """
    Get player image URL by name.

    Args:
        player_name: Full name of player
        player_id: Optional player ID if known (e.g., "lopezbr01")

    Returns:
        Image URL if found, None otherwise
    """
    if player_id:
        # Use provided player ID
        first_letter = player_id[0]
        url = f"https://www.basketball-reference.com/players/{first_letter}/{player_id}.html"
    else:
        # Generate URL from name
        url = get_player_url(player_name)

    return scrape_player_image(url)


def test_with_example_html():
    """Test parsing with example HTML from example_scraper.py"""
    print("Test 1: Parsing example HTML (Brook Lopez)")
    print("-" * 60)

    # Read example HTML
    with open('example_scraper.py', 'r') as f:
        content = f.read()
        # Extract HTML from triple-quoted string
        html = content.split('"""')[1]

    img_url = parse_player_image_from_html(html)
    if img_url:
        print(f"[SUCCESS] Image URL: {img_url}")
    else:
        print(f"[FAILED] Could not parse image URL")
    print()


def test_live_scraping():
    """Test live scraping (may fail due to anti-bot measures)"""
    print("\nTest 2: Live scraping (may be blocked by Basketball Reference)")
    print("-" * 60)

    test_players = [
        ("Brook Lopez", "lopezbr01"),
        ("Michael Jordan", "jordami01"),
        ("Marques Johnson", "johnsom01")
    ]

    for player_name, player_id in test_players:
        print(f"\nPlayer: {player_name} (ID: {player_id})")

        img_url = get_player_image(player_name, player_id)

        if img_url:
            print(f"[SUCCESS] Image URL: {img_url}")
        else:
            print(f"[FAILED] Image not found (likely blocked)")

        # Delay between requests
        time.sleep(2)


if __name__ == "__main__":
    print("Basketball Reference Image Scraper Test Suite")
    print("=" * 60)

    # Test 1: Parse example HTML (will work)
    test_with_example_html()

    # Test 2: Live scraping (may be blocked)
    test_live_scraping()

    print("\n" + "=" * 60)
    print("\nNote: If live scraping fails due to 403 errors,")
    print("use parse_player_image_from_html() with manually fetched HTML.")
