# Discord Testing Guide - Collection System

## ✅ Prerequisites

1. Bot is integrated into Discord server
2. You have permissions to use commands
3. Players exist in the database (should have been loaded from ADP board)

---

## 🚀 Step 1: Start the Bot

```bash
python bot.py
```

**Expected console output:**
```
✅ SpawningCog loaded
✅ CollectionCog loaded
Synced 2 command(s) to guild 'YourServer' (INSTANT)
Synced commands: ['recognize', 'collection']
```

If you see both cogs loaded and both commands synced, you're ready to test!

---

## 🎮 Step 2: Test Player Spawning & Catching

### A. Trigger a Spawn

1. **Send 5 messages** in any channel (threshold is set to 5 for testing)
   ```
   test
   test
   test
   test
   test
   ```

2. **A player should spawn:**
   ```
   🏀 A wild NBA player appeared!
   Use /recognize <player name> to catch them!
   [Image of the player]
   ```

### B. Catch the Player (First Time)

3. **Type the slash command:**
   ```
   /recognize LeBron James
   ```
   *(Replace with the actual player name that spawned)*

4. **Expected response:**
   ```
   ✅ Player Caught!
   @YourName caught LeBron James!

   Rarity: GOAT
   ADP: 1.5
   Status: 🆕 New player added to your collection!
   ```

### C. Catch the Same Player Again (Duplicate Test)

5. **Send 5 more messages** to trigger another spawn

6. **If the same player spawns, catch them again:**
   ```
   /recognize LeBron James
   ```

7. **Expected response:**
   ```
   ✅ Player Caught!
   @YourName caught LeBron James!

   Rarity: GOAT
   ADP: 1.5
   Status: ⚠️ You already owned this player!
   ```

**Notice:** The status changes to "already owned"!

---

## 📋 Step 3: View Your Collection

### A. View Your Own Collection

1. **Type the slash command:**
   ```
   /collection
   ```

2. **Expected response:**
   ```
   🏀 YourName's Collection
   Total Players: 1 | Points: 1,000

   Rarity Breakdown
   GOAT: 1

   LeBron James (GOAT)
   Caught: 2026-01-18

   Page 1/1
   ```

3. **You should see 5 navigation buttons:**
   - ⏮️ First
   - ◀️ Prev
   - Page 1/1 (green, disabled)
   - Next ▶️
   - Last ⏭️

### B. View Another User's Collection

4. **Type the slash command with a user mention:**
   ```
   /collection @FriendName
   ```

5. **Expected response:**
   ```
   🏀 FriendName's Collection
   Total Players: 0 | Points: 0

   No players yet!
   Start recognizing players to build your collection.

   Page 1/1
   ```

---

## 🔄 Step 4: Test Pagination

### A. Build a Collection with 10+ Players

1. **Catch 10 different players** (send 5 messages, recognize, repeat)

2. **View your collection:**
   ```
   /collection
   ```

3. **You should see:**
   - First 9 players on page 1
   - "Page 1/2" indicator

### B. Navigate Pages

4. **Click "Next ▶️" button**
   - Should show page 2 with remaining players
   - "First" and "Prev" buttons should be enabled
   - Page indicator should show "Page 2/2"

5. **Click "◀️ Prev" button**
   - Should go back to page 1
   - "Next" and "Last" buttons should be enabled

6. **Click "Last ⏭️" button**
   - Should jump to the last page

7. **Click "⏮️ First" button**
   - Should jump back to page 1

---

## ⏰ Step 5: Test Timeout Behavior

1. **Open your collection:**
   ```
   /collection
   ```

2. **Wait 3+ minutes** (timeout is 180 seconds)

3. **Expected behavior:**
   - All navigation buttons become disabled/grayed out
   - Clicking buttons does nothing
   - This prevents errors from stale views

---

## 📊 Step 6: Test Statistics

### A. Check Point Calculation

1. **Catch players of different rarities:**
   - GOAT (1000 points)
   - Mythic (500 points)
   - Legendary (250 points)
   - Epic (100 points)
   - Rare (50 points)
   - Common (10 points)

2. **View your collection:**
   ```
   /collection
   ```

3. **Verify the "Total Points" matches:**
   - Example: 2 GOAT + 1 Mythic = 2000 + 500 = 2,500 points

### B. Check Rarity Breakdown

4. **The "Rarity Breakdown" should show:**
   ```
   GOAT: 2 | Mythic: 1
   ```
   *(Counts for each rarity tier)*

---

## 🐛 Troubleshooting

### Commands Don't Appear

**Problem:** `/recognize` or `/collection` don't show up in Discord

**Solutions:**
1. Wait 5-10 seconds after bot starts (guild sync is instant but takes a moment)
2. Restart Discord (refresh command cache)
3. Check bot console for "Synced X command(s)" message
4. Ensure bot has `applications.commands` permission

### Player Doesn't Spawn

**Problem:** Sent 5 messages but no spawn

**Solutions:**
1. Check bot console for message count logs
2. Ensure bot is not ignoring the channel
3. Ensure messages aren't commands (bot doesn't count command messages)
4. Try in a different channel

### "/recognize" Says No Player to Recognize

**Problem:** Player spawned but command doesn't work

**Solutions:**
1. Ensure you're in the same channel where the player spawned
2. Type the player's name exactly as shown (case/accents don't matter, but spelling does)
3. Check if someone else already caught the player (clears the spawn)

### Collection Doesn't Show Players

**Problem:** Caught players but collection is empty

**Solutions:**
1. Check bot console for database errors
2. Verify database file exists and is writable
3. Run verification script: `python verify_collection_system.py`
4. Check if using correct server (collections are server-specific)

### Buttons Don't Work

**Problem:** Navigation buttons don't respond

**Solutions:**
1. Check if timeout occurred (3 minutes = buttons disable)
2. Close and reopen collection (`/collection` again)
3. Check bot console for errors
4. Ensure bot has permission to edit messages

---

## ✅ Success Checklist

Use this to verify everything works:

- [ ] Bot starts without errors
- [ ] Console shows both cogs loaded
- [ ] Both commands (`recognize`, `collection`) sync
- [ ] Player spawns after 5 messages
- [ ] `/recognize` catches player successfully
- [ ] First catch shows "🆕 New player added"
- [ ] Duplicate catch shows "⚠️ You already owned this player"
- [ ] `/collection` displays your collection
- [ ] Collection shows correct player count
- [ ] Collection shows correct total points
- [ ] Rarity breakdown is accurate
- [ ] Navigation buttons appear
- [ ] Clicking "Next" goes to next page (if multiple pages)
- [ ] Clicking "Prev" goes to previous page
- [ ] Clicking "First" jumps to first page
- [ ] Clicking "Last" jumps to last page
- [ ] Page indicator updates correctly
- [ ] Buttons disable after 3 minute timeout
- [ ] `/collection @User` shows other user's collection

---

## 🎯 Quick Test Script

**Copy/paste this into Discord to test everything quickly:**

```
Step 1: Trigger spawn
test
test
test
test
test

Step 2: Catch player (replace with actual player name)
/recognize LeBron James

Step 3: View collection
/collection

Step 4: Test duplicate (send 5 messages, catch same player)
test
test
test
test
test
/recognize LeBron James

Step 5: Check duplicate message appears
```

---

## 📸 Expected Screenshots

If you want to verify visually, here's what you should see:

### Spawn Embed:
- Title: "🏀 A wild NBA player appeared!"
- Image of player
- Color matches rarity (Red=GOAT, Purple=Mythic, etc.)

### Catch Embed (New):
- Title: "✅ Player Caught!"
- Green color
- Status: "🆕 New player added to your collection!"

### Catch Embed (Duplicate):
- Title: "✅ Player Caught!"
- Gold color
- Status: "⚠️ You already owned this player!"

### Collection Embed:
- Title: "🏀 [Username]'s Collection"
- Gold color
- Rarity breakdown section
- Player cards (name, rarity, caught date)
- 5 navigation buttons at bottom
- Footer: "Page X/Y"

---

## 🎉 You're All Set!

If all tests pass, the collection system is working perfectly on Discord!

**Need help?** Check the console logs for detailed error messages.

**Want to verify database integrity?** Run:
```bash
python verify_collection_system.py
```
