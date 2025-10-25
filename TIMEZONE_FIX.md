# ⏰ Timezone Fix Applied

## What Was Wrong

News dates were displaying incorrectly in the frontend because:

1. **News API** returned dates like: `"Sat, 25 Oct 2025 02:25:00 -0400"` (EDT timezone)
2. **Database** stored these but lost timezone info → became naive `02:25:00`
3. **Backend API** treated naive datetimes as if they were already UTC
4. **Frontend** received wrong UTC time → displayed incorrectly in local timezone

### Example
- News published: 2:25 AM EDT (6:25 AM UTC, 5:25 PM AEDT)
- Old backend sent: `2025-10-25T02:25:00Z` (wrong! treated 2:25 as UTC)
- Frontend displayed: 1:25 PM AEDT (wrong!)

## What Was Fixed

### Backend Changes

**File: `/app/news_service.py`**
- Now converts all dates to UTC **before** storing in database
- Stores as naive UTC (consistent format)

**File: `/app/server.py`**
- Treats stored dates as UTC (which they now are)
- Returns proper UTC ISO strings with `Z` suffix

### Result

- News published: 2:25 AM EDT
- Converted to UTC: 6:25 AM UTC
- Stored in DB: `2025-10-25 06:25:00` (naive UTC)
- Backend sends: `2025-10-25T06:25:00Z`
- Frontend displays: 5:25 PM AEDT ✅ Correct!

## What You Need to Do

### Option 1: Wait for Fresh News (Easiest)

The backend fetches news every 5 minutes. New articles will have correct timestamps automatically.

Just wait 5-10 minutes and refresh the dashboard.

### Option 2: Force Refresh Now

Manually trigger a news fetch:

```bash
curl -X POST http://localhost:8000/api/runs/refresh
```

Or if using your VPS:

```bash
curl -X POST http://134.199.159.103:8000/api/runs/refresh
```

### Option 3: Clear Old Data (Nuclear)

If you want to remove all old news with incorrect timestamps:

```bash
# Backup first!
cd /Users/rileymartin/tradingbot
sqlite3 trading_bot.db "DELETE FROM news_articles;"
```

Then let the backend fetch fresh news.

## Verification

After the fix:

1. Check backend API:
```bash
curl http://localhost:8000/api/news | jq '.[0].date'
```

Should see UTC times like: `"2025-10-25T06:25:00Z"`

2. Check frontend:
Open http://localhost:3000

News times should now match your local timezone correctly!

## Technical Details

### Before
```python
# Parsed with timezone but stored naive (loses tz info)
date = datetime.strptime("02:25:00 -0400", ...)  # EDT
# Stored: 02:25:00 (naive, timezone lost!)
# API sends: 02:25:00Z (wrong! not UTC)
```

### After
```python
# Parse, convert to UTC, store naive
dt = datetime.strptime("02:25:00 -0400", ...)    # EDT
dt_utc = dt.astimezone(timezone.utc)             # 06:25 UTC
date = dt_utc.replace(tzinfo=None)                # Store 06:25 naive
# API sends: 06:25:00Z (correct! properly UTC)
```

## Files Modified

- ✅ `/app/news_service.py` - Date parsing and UTC conversion
- ✅ `/app/server.py` - API response formatting

## Restart Required

**Backend:** Yes, restart to apply changes

```bash
cd /Users/rileymartin/tradingbot
./stop_all.sh
./start.sh
```

**Frontend:** No changes needed, it already handles timezones correctly!

---

✅ **Fix complete!** New articles will have correct timestamps.

