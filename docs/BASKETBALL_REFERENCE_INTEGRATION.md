# Basketball Reference Integration Guide

## Overview

HooperTwo uses **Basketball Reference as the primary and only image source** for all player images. This provides comprehensive coverage of both active and historical NBA players through direct image URLs.

**Key Facts:**
- Basketball Reference provides direct image URLs (no HTML scraping required)
- 99.8% ADP board coverage (449/450 players)
- Direct URL format eliminates need for page scraping
- Discord allows hotlinking - URLs stored in database, embedded directly

## Architecture

### Single-Source Design

```
┌─────────────────────────────────────────────────────┐
│            BasketballReferenceClient                │
│    Primary and only image source                    │
└───────────────┬─────────────────────────────────────┘
                │
    ┌───────────▼────────────────────┐
    │  Basketball Reference          │
    │  Direct Image URLs             │
    │  (No HTML scraping)            │
    └────────────────────────────────┘
```

### Complementary Role of NBA API

```
┌─────────────────────────────────────────────────────┐
│              NBAApiClient                           │
│    Player statistics and filtering only             │
└───────────────┬─────────────────────────────────────┘
                │
    ┌───────────▼────────────────────┐
    │  NBA.com API                   │
    │  - Player search               │
    │  - Career statistics           │
    │  - Games played filtering      │
    └────────────────────────────────┘
```

**Separation of Concerns:**
- `NBAApiClient`: Player stats and filtering (>1000 career minutes)
- `BasketballReferenceClient`: ALL image handling

## Direct Image URL Format

Basketball Reference provides direct image URLs that return 404 if the image doesn't exist:

```
https://www.basketball-reference.com/req/202106291/images/headshots/{player_id}.jpg
```

**Examples:**
```
Michael Jordan:  .../images/headshots/jordami01.jpg
LeBron James:    .../images/headshots/jamesle01.jpg
Stephen Curry:   .../images/headshots/curryst01.jpg
```

**Response Codes:**
- `200 OK`: Image exists and is available
- `404 Not Found`: No image for this player ID
- `403 Forbidden`: Rate limited (temporary, exponential backoff)
- `429 Too Many Requests`: Rate limited (temporary, exponential backoff)

## BasketballReferenceClient

### Core Methods

#### 1. `construct_image_url(player_id: str) -> str`

Constructs direct Basketball Reference image URL.

```python
url = client.construct_image_url("jordami01")
# Returns: "https://www.basketball-reference.com/req/202106291/images/headshots/jordami01.jpg"
```

#### 2. `verify_image_url(url: str, max_retries: int = 5) -> bool`

Verifies image URL exists with exponential backoff for rate limiting.

```python
exists = client.verify_image_url("https://...jordami01.jpg")
# Returns: True if 200, False if 404 or max retries exceeded
```

**Exponential Backoff Strategy:**
- Retry only on 403/429 (rate limiting)
- Base delay: 2 seconds
- Delay formula: `2^attempt` seconds
- Max retries: 5 (total max wait: 2+4+8+16+32 = 62 seconds)
- 404 responses: No retry (image doesn't exist)

**Example sequence:**
```
Attempt 1: 403 → Wait 2s
Attempt 2: 403 → Wait 4s
Attempt 3: 403 → Wait 8s
Attempt 4: 200 → Success!
```

#### 3. `get_player_image_url(player_name: str) -> Optional[str]`

Main method combining player ID lookup, URL construction, and verification.

```python
url = client.get_player_image_url("Michael Jordan")
# Returns: "https://...jordami01.jpg" or None if not found
```

**Process:**
1. Enforce rate limit (10 requests/minute)
2. Look up player ID from database
3. Construct direct image URL
4. Verify URL exists (with exponential backoff)
5. Return URL or None

### Player ID Database

**Location:** `data/player_ids.json`

**Structure:**
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
      "url": "https://www.basketball-reference.com/players/p/playero01.html"
    }
  },
  "needs_verification": []
}
```

**Coverage:**
- 46 verified player IDs (manually confirmed)
- 403 estimated player IDs (algorithmic generation)
- 99.8% ADP board coverage (449/450 players)
- Missing: JR Smith (requires manual addition)

**ID Sections:**
- `verified`: Manually confirmed player IDs with verified image URLs
- `estimated`: Algorithmically generated IDs (may need verification if image fails)
- `needs_verification`: Players requiring manual ID lookup

### Rate Limiting

**Conservative Strategy:**
- Default: 10 requests/minute
- Uses sliding window (removes requests >60s old)
- Automatic sleep if limit reached

```python
client = BasketballReferenceClient(
    rate_limit_per_minute=10  # Conservative for BR
)
```

**Why Conservative?**
- Avoids 403 blocking from Basketball Reference
- Combined with exponential backoff, ensures reliability
- Acceptable for batch operations (seeding can take hours)

## Usage Examples

### Basic Usage

```python
from src.scrapers.basketball_reference_client import BasketballReferenceClient

# Initialize client
client = BasketballReferenceClient(
    player_id_db_path="data/player_ids.json",
    rate_limit_per_minute=10
)

# Get image URL for a player
image_url = client.get_player_image_url("LeBron James")

if image_url:
    print(f"Image URL: {image_url}")
    # Store in database, embed in Discord
else:
    print("No image found")
```

### Batch Processing (Seeder Script)

The seeding script (`scripts/seed_all_players.py`) processes players in two phases:

**Phase 1: Scoring CSV Processing**
```python
from src.scrapers.basketball_reference_client import BasketballReferenceClient
from src.database.repositories.player_repository import PlayerRepository

# Initialize
br_client = BasketballReferenceClient(
    player_id_db_path="data/player_ids.json",
    rate_limit_per_minute=10
)
repo = PlayerRepository(connection_manager)

# Process all players from scoring.csv
for player in all_players:
    # Get image URL from Basketball Reference
    image_url = br_client.get_player_image_url(player['name'])

    if image_url:
        # Add player with image
        repo.create_player(
            name=player['name'],
            image_url=image_url,
            rarity_tier="Common"
        )
    else:
        # Handle missing image (see ADP Board Logic section)
        pass
```

**Phase 2: Missing ADP Board Players**

After processing the scoring CSV, the script checks for ADP board players not in the CSV:

```python
# Get all ADP board players
all_adp_players = get_all_adp_players(adp_players_path)

# Find players not in scoring CSV
missing_adp_players = {
    name: obj for name, obj in all_adp_players.items()
    if name not in qualified_players
}

# Add missing ADP players to ensure 100% coverage
for player_name, player_obj in missing_adp_players.items():
    image_url = br_client.get_player_image_url(player_name)
    rarity_tier = calculate_rarity_tier(player_obj["adp"])

    repo.create_player(
        name=player_name,
        adp_value=player_obj["adp"],
        rarity_tier=rarity_tier,
        image_url=image_url,
        career_minutes=0  # No minutes data available
    )
```

**Running the Seeder:**

```bash
# Normal run (incremental, preserves existing players)
poetry run python scripts/seed_all_players.py

# Fresh start (clears database first)
poetry run python scripts/seed_all_players.py --clear
```

## ADP Board Handling Logic

The seeder script implements special handling for ADP board players to ensure no data loss and 100% coverage.

### Two-Phase Processing

**Phase 1: Scoring CSV Players**

Players from scoring.csv (>1000 career minutes) are processed with the following logic:

### Three-Way Decision Logic (Scoring CSV Players)

```python
# Check if player is on ADP board
on_adp_board = is_on_adp_board(player_name, repo)

# Get image URL from Basketball Reference
image_url = br_client.get_player_image_url(player_name)

if image_url:
    # ✓ Has image - add to database
    repo.create_player(
        name=player_name,
        adp_value=None,  # Will be set by ADP loader
        rarity_tier="Common",
        image_url=image_url,
        career_minutes=career_minutes
    )

elif on_adp_board:
    # ⚠️ ADP board player WITHOUT image - LOG and store with NULL
    logger.error(f"ADP BOARD PLAYER MISSING IMAGE: {player_name}")
    logger.error(f"   Manual intervention required!")

    repo.create_player(
        name=player_name,
        adp_value=None,
        rarity_tier="Common",
        image_url=None,  # NULL - needs manual fix
        career_minutes=career_minutes
    )

else:
    # ✗ Not on ADP board, no image - skip entirely
    logger.debug(f"Skipping {player_name} (no image, not on ADP board)")
    continue
```

### Rationale

**Why store NULL for ADP board players?**
- Preserves player data for high-value players
- Allows manual intervention later
- Prevents data loss for important players
- Final statistics report highlights players needing attention

**Why skip non-ADP players?**
- Lower priority (Common rarity)
- Reduces database clutter
- Only includes players with complete data
- Focuses manual effort on high-value players

### Estimated ID Logging

When an image lookup fails, log if it used an estimated player ID:

```python
if not image_url:
    # Check if failure was due to estimated ID
    player_id = br_client.find_player_id(player_name)
    if player_id:
        db = br_client._load_player_id_database()
        if player_name in db['estimated']:
            logger.warning(f"Estimated player ID failed: {player_name} → {player_id}")
            logger.warning(f"   Consider manual verification and moving to 'verified'")
```

This helps identify player IDs that need manual verification.

### Phase 2: Missing ADP Board Players

After processing all players from the scoring CSV, the script checks for ADP board players that weren't in the CSV:

```python
# Get all ADP players (verified + estimated)
all_adp_players = get_all_adp_players(adp_players_path)

# Find players not in scoring CSV
missing_adp_players = {
    name: obj for name, obj in all_adp_players.items()
    if name not in qualified_players
}

logger.info(f"Found {len(missing_adp_players)} ADP board players not in scoring.csv")

# Process each missing ADP player
for player_name, player_obj in missing_adp_players.items():
    # Skip if already in database (e.g., manually added)
    if repo.get_player_by_name(player_name):
        continue

    # Get image URL and ADP value
    image_url = br_client.get_player_image_url(player_name)
    adp_value = player_obj.get("adp")
    rarity_tier = calculate_rarity_tier(adp_value)

    # Add player with ADP rarity (even without image)
    repo.create_player(
        name=player_name,
        adp_value=adp_value,
        rarity_tier=rarity_tier,
        image_url=image_url,  # NULL if not found
        career_minutes=0  # No minutes data from CSV
    )
```

**Why This Matters:**

- **100% ADP Coverage**: Ensures every player on the ADP board is in the database
- **No Manual Work**: Automatically catches players missing from scoring.csv
- **Common Cases**:
  - Rookies/young players with <1000 career minutes
  - Players with incomplete stats in scoring.csv
  - Historical players missing from the CSV

**Statistics Tracked:**
- `missing_adp_processed`: Total missing ADP players checked
- `missing_adp_added`: Players added with valid images
- `missing_adp_no_image`: Players added without images (flagged)
- `missing_adp_already_exists`: Players already in database

## Image Verification System

Basketball Reference uses Cloudflare protection that blocks standard HTTP HEAD/GET requests for image URL verification. To bypass this, HooperTwo uses **nodriver** (lightweight Chrome automation) to verify images before adding players to the database.

### Architecture

```
┌──────────────────────────────────────────────────────┐
│              ImageVerifier                           │
│   Cloudflare bypass via nodriver browser             │
└───────────────┬──────────────────────────────────────┘
                │
    ┌───────────▼────────────────────┐
    │  Nodriver Browser              │
    │  - Chrome DevTools Protocol    │
    │  - Automatic fingerprint mask  │
    │  - Async/await pattern         │
    └────────────────────────────────┘
                │
    ┌───────────▼────────────────────┐
    │  Basketball Reference          │
    │  (Protected by Cloudflare)     │
    └────────────────────────────────┘
```

### Why Nodriver?

**Cloudflare Protection Issue:**
- Standard HTTP requests (`requests`, `aiohttp`) are blocked by Cloudflare
- HEAD requests return 403 Forbidden even with proper headers
- Basketball Reference uses aggressive bot detection

**Nodriver Solution:**
- Lightweight successor to undetected-chromedriver (~30-50MB)
- Direct Chrome DevTools Protocol communication (fewer automation traces)
- Fully async for efficient resource usage
- Automatic fingerprint masking (appears as legitimate browser to Cloudflare)
- [Best free Cloudflare bypass solution for 2026](https://scrapfly.io/blog/posts/how-to-bypass-cloudflare-anti-scraping)

**Alternatives Considered:**
- ❌ HTTP HEAD requests: Completely blocked by Cloudflare (confirmed)
- ❌ SeleniumBase UC Mode: Must run non-headless (visible browser), more resource-intensive
- ❌ Playwright: Heavier (~120MB vs 30-50MB), more overhead than nodriver

### ImageVerifier Class

**Location:** `src/scrapers/image_verifier.py`

**Core Method:**

```python
from src.scrapers.image_verifier import ImageVerifier

# Initialize verifier
verifier = ImageVerifier(rate_limit_delay=2.5)

# Verify image URL (async)
is_valid = await verifier.verify_image_url(image_url)

# Cleanup
await verifier.close()
```

**Features:**
- **Browser Instance Reuse:** Single browser for entire batch (efficient)
- **Rate Limiting:** 2-3 seconds between checks (configurable)
- **Retry Logic:** Exponential backoff for transient failures (max 3 retries)
- **404 Detection:** Checks page content for "Page Not Found (404 error)"
- **Lazy Initialization:** Browser only starts on first verification request

### Integration with Seeding Script

The seeding script (`scripts/seed_all_players.py`) integrates ImageVerifier with special handling for ADP board players:

```python
# Initialize ImageVerifier
image_verifier = ImageVerifier(rate_limit_delay=2.5)

# For each player...
image_url = br_client.get_player_image_url(player_name)

# Verify image exists (unless ADP player - those skip verification)
if image_url and not on_adp_board:
    is_valid = asyncio.run(image_verifier.verify_image_url(image_url))

    if not is_valid:
        image_url = None  # Mark as invalid
        skip_list.add_skipped_player(player_name, 'no_image')
        logger.info(f"Image verification failed for {player_name}")

# Cleanup at end
asyncio.run(image_verifier.close())
```

**Key Behaviors:**
- ✅ **Non-ADP players:** Images are verified before adding to database
- ✅ **Invalid images:** Player added to skip list, not added to database
- ✅ **ADP board players:** Skip verification entirely (see ADP Exception below)
- ✅ **Skip list caching:** Invalid images cached, no re-verification on subsequent runs

### ADP Exception Path

**ADP board players bypass image verification entirely.** This prevents high-value players from being excluded due to image verification failures.

```python
# ADP players skip verification
if image_url and not on_adp_board:
    # Only verify for non-ADP players
    is_valid = asyncio.run(image_verifier.verify_image_url(image_url))
```

**Rationale:**
- ADP board players are high-value (rare/mythic/legendary)
- Must be included in database even without valid images
- Added with NULL image_url, flagged for manual fixing
- Preserves player data for important players

**ADP Player Without Image:**
```python
elif on_adp_board and not image_url:
    # ADP board player WITHOUT image - LOG and store with NULL
    logger.error(f"ADP BOARD PLAYER MISSING IMAGE: {player_name}")
    repo.create_player(
        name=player_name,
        image_url=None,  # NULL - needs manual fix
        rarity_tier=calculated_rarity,
        career_minutes=career_minutes
    )
```

### Skip List Caching

The skip list (`data/skipped_players.json`) provides permanent caching of verification results:

**First Run:**
- All ~4000 players verified with nodriver (~3-4 hours)
- Invalid images added to skip list with reason 'no_image'

**Subsequent Runs:**
- Skip list checked BEFORE verification
- Cached players skip browser verification entirely
- Only new/uncached players are verified (~minutes only)

**Performance Impact:**
```
First run:    ~3-4 hours (2.5s per player × 4000 players)
Second run:   ~5-10 minutes (only delta players verified)
Third+ runs:  ~5-10 minutes (only new players verified)
```

### Rate Limiting Configuration

**Default Settings:**
```python
ImageVerifier(rate_limit_delay=2.5)  # 2.5 seconds between requests
```

**Rationale:**
- Balances speed vs Cloudflare safety
- 2.5s per player = ~2.5 hours for 3600 players (first run)
- Subsequent runs only verify new players (~minutes)
- Conservative to avoid triggering Cloudflare rate limits

**Tuning:**
```python
# More aggressive (use with caution)
ImageVerifier(rate_limit_delay=1.5)  # 1.5s between requests

# More conservative (safer, slower)
ImageVerifier(rate_limit_delay=5.0)  # 5s between requests
```

### Testing

**Unit Tests:** `tests/test_scrapers/test_image_verifier.py`

```bash
# Run unit tests (fast, with mocked browser)
pytest tests/test_scrapers/test_image_verifier.py -m "not integration" -v

# Run integration tests (slow, real browser + network)
pytest tests/test_scrapers/test_image_verifier.py -m integration -v
```

**Integration Tests:** `tests/scripts/test_seed_all_players_with_verification.py`

```bash
# Test seeding script integration
pytest tests/scripts/test_seed_all_players_with_verification.py -v
```

**Test Coverage:**
- ✅ Valid Basketball Reference image URL → returns True
- ✅ Invalid Basketball Reference image URL (404) → returns False
- ✅ Rate limiting enforcement (verify delays between calls)
- ✅ Browser instance reuse and cleanup
- ✅ Retry logic with exponential backoff
- ✅ ADP players skip verification
- ✅ Skip list caching prevents re-verification

### Troubleshooting

#### Issue: Nodriver installation fails

**Symptoms:** Import error or Chrome download fails

**Solutions:**
```bash
# Install nodriver
poetry add nodriver

# Or with pip
pip install nodriver

# Chrome will download automatically on first run (~100MB)
```

#### Issue: Verification is very slow

**Symptoms:** First run takes >4 hours

**Explanation:**
- Expected behavior for ~4000 players at 2.5s per player
- First run always slow (must verify all images)
- Subsequent runs are fast (skip list caching)

**Solutions:**
- ✓ Accept the first-run time (one-time operation)
- ✓ Run in background/overnight
- ⚠️ Reduce rate_limit_delay (increases Cloudflare block risk)

#### Issue: Cloudflare blocks/challenges

**Symptoms:** Browser shows Cloudflare challenge page, all verifications fail

**Solutions:**
1. **Increase rate limit delay:**
   ```python
   ImageVerifier(rate_limit_delay=5.0)  # More conservative
   ```

2. **Wait and retry:**
   - Temporary block usually lifts in 30-60 minutes
   - Run verification again later

3. **Check skip list:**
   - Review `data/skipped_players.json`
   - Previously verified players won't be re-checked

#### Issue: Browser doesn't close properly

**Symptoms:** Chrome processes remain after script ends

**Solutions:**
```python
# Always use try/finally for cleanup
verifier = ImageVerifier()
try:
    result = await verifier.verify_image_url(url)
finally:
    await verifier.close()
```

### Best Practices

**Do's:**
- ✓ Use rate_limit_delay of 2-3 seconds minimum
- ✓ Always call `verifier.close()` when done
- ✓ Trust skip list caching (don't force re-verification)
- ✓ Run first seeding overnight (takes 3-4 hours)
- ✓ ADP players always bypass verification

**Don'ts:**
- ✗ Don't reduce rate_limit_delay below 1.5s (Cloudflare risk)
- ✗ Don't delete skip list (forces re-verification of all players)
- ✗ Don't verify ADP players (exception path exists for this)
- ✗ Don't create multiple ImageVerifier instances (browser overhead)

## Integration with HooperTwo

### Database Storage

Player images are stored as URLs in the database:

```sql
CREATE TABLE players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    image_url TEXT,  -- Basketball Reference direct URL
    adp_value REAL,
    rarity_tier TEXT NOT NULL,
    career_minutes INTEGER
);
```

### Discord Embedding

Discord allows hotlinking - embed URLs directly:

```python
embed = discord.Embed(title=player_name)
embed.set_image(url=image_url)  # Direct BR URL
await ctx.send(embed=embed)
```

**No local caching needed:**
- URLs work directly in Discord embeds
- No download/storage overhead
- Basketball Reference allows hotlinking
- Simpler architecture

## Testing

### Test Suite

**Location:** `tests/test_scrapers/test_basketball_reference_client.py`

**Coverage:** 17 comprehensive tests

```bash
python -m pytest tests/test_scrapers/test_basketball_reference_client.py -v
```

**Test Categories:**

1. **Initialization** (1 test)
   - Client initialization with rate limit

2. **Player ID Lookup** (3 tests)
   - Verified player IDs
   - Estimated player IDs
   - Players not in database

3. **URL Construction** (2 tests)
   - Direct image URL construction
   - Player page URL construction

4. **URL Verification** (5 tests)
   - Success (200)
   - Not found (404)
   - Rate limiting with exponential backoff (403)
   - Max retries exceeded
   - Request exceptions

5. **Integration** (3 tests)
   - Get image URL for verified player
   - Player not in database
   - Image doesn't exist (404)

6. **Utilities** (3 tests)
   - Database caching
   - Missing database file handling
   - Rate limiting mechanism
   - HTTP headers

### Running Full Test Suite

```bash
# All scraper tests
python -m pytest tests/test_scrapers/ -v

# With coverage
python -m pytest tests/test_scrapers/ --cov=src/scrapers --cov-report=html
```

## Performance Characteristics

### Speed

**Typical Response Times:**
- Player ID lookup: <1ms (cached in memory)
- URL construction: <1ms (string formatting)
- URL verification: 100-500ms (HEAD request)
- Total: ~100-500ms per player

**Rate Limiting Impact:**
- 10 requests/minute = 6 seconds between requests
- 450 ADP board players = ~45 minutes to verify all
- Acceptable for batch seeding operations

### Coverage

| Category | Coverage | Notes |
|----------|----------|-------|
| ADP Board Players | 99.8% (449/450) | Only JR Smith missing |
| Active Players | ~95% | Most current NBA players |
| Historical Players | ~90% | Major historical figures |
| Total Database | 449 players | Verified + Estimated |

### Reliability

**Success Factors:**
- Direct URLs eliminate HTML parsing failures
- Exponential backoff handles rate limiting
- Conservative rate limits avoid blocks
- HEAD requests are lightweight

**Failure Modes:**
- Player not in database → Returns None
- Image doesn't exist (404) → Returns None (no retry)
- Rate limited (403/429) → Exponential backoff, returns True/False
- Network error → Exponential backoff, returns False after retries

## Maintenance

### Adding New Players

When new players appear on ADP board:

1. **Identify Missing Players**
   ```bash
   python test_all_players.py
   # Outputs: Players not found in database
   ```

2. **Look Up Player ID**
   - Visit: `https://www.basketball-reference.com/`
   - Search for player name
   - Extract ID from URL: `.../players/X/{player_id}.html`

3. **Add to Database**
   ```json
   {
     "verified": {
       "JR Smith": {
         "player_id": "smithjr01",
         "adp": 303.37,
         "url": "https://www.basketball-reference.com/players/s/smithjr01.html"
       }
     }
   }
   ```

4. **Verify URL**
   ```bash
   curl -I https://www.basketball-reference.com/req/202106291/images/headshots/smithjr01.jpg
   # Should return: HTTP/1.1 200 OK
   ```

### Rate Limit Tuning

If experiencing frequent 403 errors:

```python
# More conservative
client = BasketballReferenceClient(
    rate_limit_per_minute=5  # Half speed
)

# Or increase backoff max retries
def verify_image_url(self, url: str, max_retries: int = 10):
    # Allows more retry attempts
```

### Database Cleanup

Periodically verify estimated IDs:

1. **Run seeder with logging enabled**
2. **Review estimated ID failures in logs**
3. **Manually verify failed player IDs**
4. **Move verified IDs to "verified" section**

## Troubleshooting

### Issue: Player image not found

**Symptoms:** `get_player_image_url()` returns None

**Diagnosis:**
1. Check if player in database: `client.find_player_id(player_name)`
2. If None → Player not in database, needs manual addition
3. If returns ID → Check if image URL returns 404

**Solutions:**
- Add player to `data/player_ids.json`
- Verify exact name spelling matches database
- Check Basketball Reference manually

### Issue: 403 Forbidden errors

**Symptoms:** All requests fail with 403 after initial success

**Diagnosis:**
- Temporarily rate limited by Basketball Reference
- Too many requests in short period

**Solutions:**
1. Reduce rate limit: `rate_limit_per_minute=5`
2. Increase backoff delays
3. Wait 30-60 minutes before retrying
4. Verify User-Agent header is set

### Issue: Slow batch processing

**Symptoms:** Seeding takes many hours

**Explanation:**
- 10 requests/minute = 6 seconds per player
- 450 players × 6 seconds = 45 minutes minimum
- With rate limiting pauses, can take 1-2 hours

**This is expected and acceptable:**
- One-time operation during initial setup
- Background task, doesn't block bot operation
- Ensures compliance with Basketball Reference rate limits

## Best Practices

### Do's

✓ Always check return value of `get_player_image_url()` for None
✓ Store URLs directly in database (no local caching)
✓ Use conservative rate limits (10 requests/minute)
✓ Log estimated ID failures for manual verification
✓ Handle missing images gracefully in bot commands

### Don'ts

✗ Don't scrape HTML (use direct URLs)
✗ Don't bypass rate limiting (causes 403 blocks)
✗ Don't cache images locally (unnecessary with hotlinking)
✗ Don't skip ADP board players without logging
✗ Don't assume all players have images

## Related Files

**Core:**
- `src/scrapers/basketball_reference_client.py` - Basketball Reference client implementation
- `src/scrapers/nba_api_client.py` - NBA API client (stats only, no images)
- `data/player_ids.json` - Player ID database

**Scripts:**
- `scripts/seed_all_players.py` - Batch player seeding with ADP logic
- `test_all_players.py` - Player ID coverage testing

**Tests:**
- `tests/test_scrapers/test_basketball_reference_client.py` - BR client tests (17 tests)
- `tests/test_scrapers/test_nba_api_client.py` - NBA client tests (3 tests)

**Documentation:**
- `docs/plans/2026-01-04-hooper-two-nba-bot.md` - Implementation plan
- `docs/BASKETBALL_REFERENCE_INTEGRATION.md` - This guide

## Resources

- [Basketball Reference](https://www.basketball-reference.com/) - Official site
- [Basketball Reference Player Index](https://www.basketball-reference.com/players/) - Player ID lookup
- [Direct Image URL Format](https://www.basketball-reference.com/req/202106291/images/headshots/) - Image directory
