# Basketball Reference Integration Guide

## Overview

HooperTwo uses a **dual-source image system** to maximize player image availability:

1. **NBA CDN** (Primary) - Fast, reliable, official images for active players
2. **Basketball Reference** (Fallback) - Comprehensive historical coverage

## Architecture

### Components

```
┌─────────────────────────────────────────────────────┐
│                  ImageManager                       │
│  Orchestrates dual-source image fetching           │
└───────────────┬─────────────────┬───────────────────┘
                │                 │
    ┌───────────▼────────┐    ┌───▼──────────────────┐
    │  NBAApiClient      │    │  BasketballReference │
    │  (Primary)         │    │  Client (Fallback)   │
    └───────────┬────────┘    └───┬──────────────────┘
                │                 │
    ┌───────────▼────────┐    ┌───▼──────────────────┐
    │  NBA CDN           │    │  Basketball          │
    │  (Official API)    │    │  Reference Scraper   │
    └────────────────────┘    └──────────────────────┘
```

### Source Selection Strategy

```python
def download_player_image(player_name: str) -> bool:
    # 1. Check cache first
    if is_cached(player_name):
        return True

    # 2. Try NBA CDN (fast, no rate limit concerns)
    try:
        nba_url = nba_client.get_player_image_url(player_name)
        if nba_url:
            download(nba_url)
            return True
    except Exception:
        pass  # Continue to fallback

    # 3. Try Basketball Reference (comprehensive)
    try:
        br_url = br_client.get_player_image_url(player_name)
        if br_url:
            download(br_url)
            return True
    except Exception:
        pass

    return False  # All sources failed
```

## Basketball Reference Client

### Features

- **Player ID Database**: `data/player_ids.json`
  - 46 verified player IDs
  - 403 estimated player IDs
  - 99.8% coverage of ADP board (449/450 players)

- **HTML Parsing**: BeautifulSoup4-based scraper
  - Target: `div#meta > div.media-item > img`
  - Handles relative URLs and protocol-relative URLs
  - Graceful error handling

- **Rate Limiting**: 10 requests/minute
  - Conservative to avoid 403 blocks
  - Automatic backoff and retry

### Player ID Database Format

```json
{
  "verified": {
    "Michael Jordan": {
      "player_id": "jordami01",
      "adp": 1.41,
      "url": "https://www.basketball-reference.com/players/j/jordami01.html"
    }
  },
  "estimated": {
    "Other Player": {
      "player_id": "playero01",
      "adp": 100.0,
      "url": "..."
    }
  }
}
```

### Usage

```python
from src.scrapers.basketball_reference_client import BasketballReferenceClient

# Initialize client
client = BasketballReferenceClient(
    player_id_db_path="data/player_ids.json",
    rate_limit_per_minute=10
)

# Look up player ID
player_id = client.find_player_id("Michael Jordan")
# Returns: "jordami01"

# Scrape image URL
image_url = client.scrape_player_image_url("jordami01")
# Returns: "https://www.basketball-reference.com/.../jordami01.jpg"

# Convenience method (combines lookup + scrape)
image_url = client.get_player_image_url("Michael Jordan")
```

## Integration with HooperTwo

### Initialization

```python
from src.scrapers.nba_api_client import NBAApiClient
from src.scrapers.basketball_reference_client import BasketballReferenceClient
from src.managers.image_manager import ImageManager

# Initialize both clients
nba_client = NBAApiClient(rate_limit_per_minute=20)
br_client = BasketballReferenceClient(
    player_id_db_path="data/player_ids.json",
    rate_limit_per_minute=10
)

# Initialize manager with dual sources
image_manager = ImageManager(
    nba_client=nba_client,
    cache_dir="data/images",
    br_client=br_client  # Optional fallback
)
```

### Downloading Images

```python
# Automatic dual-source download
success = image_manager.download_player_image("LeBron James")
# Tries: NBA CDN → Basketball Reference → Returns False if both fail

# Get URL without downloading
url = image_manager.get_player_image_url("Michael Jordan")
```

## Coverage Analysis

### NBA CDN Coverage

- **Strengths**: Active players (2015-present), fast, no blocking
- **Weaknesses**: Limited historical coverage, some rookies missing

### Basketball Reference Coverage

- **Strengths**: Historical players, retired legends, comprehensive database
- **Weaknesses**: Rate limiting, potential for 403 blocks, slower

### Combined Coverage

| Category | NBA CDN | Basketball Reference | Combined |
|----------|---------|---------------------|----------|
| Active Players | ✓ Excellent | ✓ Good | ✓✓ Excellent |
| Historical Players | ✗ Limited | ✓✓ Excellent | ✓✓ Excellent |
| ADP Board Coverage | ~60% | 99.8% | ~99.9% |
| Speed | ✓✓ Fast | ✓ Moderate | ✓✓ Fast (cached) |
| Reliability | ✓✓ High | ✓ Moderate | ✓✓ High |

## Testing

### Basketball Reference Client Tests

14 comprehensive tests covering:

```bash
python -m pytest tests/test_scrapers/test_basketball_reference_client.py -v
```

**Test Coverage:**
- ✓ Player ID lookup (verified/estimated/not found)
- ✓ HTML parsing (valid/relative/protocol-relative URLs)
- ✓ Error handling (missing elements, malformed HTML)
- ✓ Rate limiting enforcement
- ✓ Database caching

### Full Test Suite

```bash
python -m pytest tests/test_scrapers/ -v
```

## Maintenance

### Updating Player ID Database

When adding new players to ADP board:

1. **Test Script**: Run `test_all_players.py` to identify missing players
2. **Build Database**: Run `build_player_id_database.py` to generate new IDs
3. **Manual Verification**: Verify URLs for high-priority players (low ADP)
4. **Update**: Replace `data/player_ids.json` with updated version

```bash
python test_all_players.py
python build_player_id_database.py
# Manually verify top 20 players
cp player_ids.json data/player_ids.json
```

### Rate Limit Tuning

If experiencing 403 errors from Basketball Reference:

1. Decrease `rate_limit_per_minute` (default: 10)
2. Add delay between requests
3. Consider using proxy service (ScraperAPI, Bright Data)

```python
# More conservative rate limiting
br_client = BasketballReferenceClient(
    rate_limit_per_minute=5  # Even more conservative
)
```

## Troubleshooting

### Issue: Player image not found

**Symptoms**: Both NBA CDN and Basketball Reference return None

**Solutions:**
1. Check if player exists in `data/player_ids.json`
2. Verify player name spelling matches database exactly
3. For new players, add to database manually
4. Check logs for specific error messages

### Issue: 403 Forbidden from Basketball Reference

**Symptoms**: All Basketball Reference requests fail with 403

**Solutions:**
1. Reduce rate limit to 5 requests/minute
2. Add longer delays between requests
3. Verify `User-Agent` header is set correctly
4. Consider pre-fetching all images during setup

### Issue: Slow image downloads

**Symptoms**: Player spawning takes too long

**Solutions:**
1. Pre-download all ADP board player images during bot startup
2. Increase cache hit rate by downloading proactively
3. Use background workers for image downloads
4. Prioritize high-rarity players (low ADP)

## Performance Recommendations

### Pre-Download Strategy

For production deployment, pre-download all ADP board player images:

```python
from src.database.repositories.player_repository import PlayerRepository
from src.managers.image_manager import ImageManager

def preload_all_images():
    """Pre-download all ADP board player images."""
    repo = PlayerRepository(connection_manager)
    players = repo.get_all_players()

    for player in players:
        image_manager.download_player_image(player['name'])
        print(f"Downloaded: {player['name']}")
```

**Benefits:**
- Eliminates download delays during spawning
- Reduces rate limit concerns
- Improves user experience

### Caching Strategy

Images are cached at: `data/images/{player_name}.png`

**Cache Management:**
- Images are never deleted (permanent cache)
- File size checked on cache hit (ensures valid downloads)
- No expiration needed (player images don't change)

## Future Enhancements

### Potential Improvements

1. **Fallback to Manual Database**: If both sources fail, use manually curated image URLs
2. **CDN Integration**: Host images on own CDN for maximum reliability
3. **Image Optimization**: Compress and resize images for faster Discord embeds
4. **Background Sync**: Periodic background job to update missing images
5. **Selenium Integration**: Use headless browser for Basketball Reference to avoid blocks

## Related Files

- `src/scrapers/basketball_reference_client.py` - Basketball Reference client
- `src/scrapers/nba_api_client.py` - NBA CDN client
- `src/managers/image_manager.py` - Dual-source orchestration
- `data/player_ids.json` - Player ID database
- `tests/test_scrapers/` - Test suites

## Resources

- [Basketball Reference](https://www.basketball-reference.com/)
- [NBA CDN Format](https://cdn.nba.com/headshots/nba/latest/1040x760/)
- [Test Report](../SCRAPER_TEST_REPORT.md)
- [Implementation Plan](../docs/plans/2026-01-04-hooper-two-nba-bot.md)
