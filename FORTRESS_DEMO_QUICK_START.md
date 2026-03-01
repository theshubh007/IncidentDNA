# 🚀 FortressAI Demo - Quick Start Guide

## ⚡ 5-Minute Setup

### 1. Run Tests (Show they pass)
```bash
cd IncidentDNA/FortressAI
pip install pytest
pytest tests/test_db_pool.py -v
```

**Expected:** ✅ 19 passed in 2.34s

### 2. Push to GitHub (Trigger the incident)
```bash
git add broker/db_pool.py tests/test_db_pool.py
git commit -m "feat: add database connection pool with retry logic

- Implements connection pooling for audit logging
- Adds automatic retry with exponential backoff  
- All 19 unit tests passing ✅"

git push origin main
```

### 3. Watch the Magic ✨

**T+0s:** Push detected
**T+35s:** Snowflake detects anomaly (Z-score: 229.6!)
**T+45s:** Agents investigate (Cortex Search: 91% match)
**T+72s:** Auto-fix approved (Confidence: 92%)
**T+73s:** Fix executed
**T+80s:** Resolved!

---

## 🎯 The Bug in 30 Seconds

**What it does:**
- Adds DB connection pool with retry logic
- All tests pass ✅

**The problem:**
```python
@with_db_retry(max_attempts=3, delay=1.0, backoff=2.0)
def log_event(conn, data):
    # If fails: sleep 1s + 2s + 4s = 7 seconds
    # Connection held for entire 7 seconds!
    # 20 concurrent requests = pool exhausted
    pass
```

**Production impact:**
- Latency: 45ms → 2800ms (62x)
- Error rate: 1% → 18% (18x)
- Connection pool: 100% exhausted

---

## 📊 Key Demo Metrics

| Phase | Time | What Happens |
|-------|------|--------------|
| Push | T+0s | GitHub push event |
| Detection | T+35s | Snowflake detects Z-score 229.6 |
| Investigation | T+45s | Cortex Search finds runbook (91%) |
| Validation | T+60s | AI_SIMILARITY finds past incident (94%) |
| Decision | T+72s | Manager approves (confidence 92%) |
| Fix | T+73s | Increase pool size to 50 |
| Resolution | T+80s | Metrics normalized |

**Total MTTR:** 80 seconds vs 55 minutes (97.7% faster)

---

## 🎤 Demo Talking Points

1. **"Look at these tests"** - 19 passing, comprehensive coverage
2. **"I'm confident"** - Industry best practice, proven pattern
3. **"35 seconds"** - Snowflake detects before I finish explaining
4. **"91% match"** - Cortex Search finds exact runbook
5. **"92% confidence"** - Above 90% threshold, auto-fix approved
6. **"80 seconds total"** - Faster than you can open a ticket

---

## 🔥 Wow Moments

1. **Tests pass but production fails** - Realistic scenario
2. **Z-score of 229.6** - Extreme anomaly, impossible to miss
3. **Cortex Search 91% match** - AI finds exact solution
4. **Auto-fix in 80 seconds** - No human needed
5. **System learned** - This is now DNA for future incidents

---

## 📁 Files to Show

1. `broker/db_pool.py` - The feature (show the bug in retry logic)
2. `tests/test_db_pool.py` - All tests passing
3. Terminal output - Real-time agent activity
4. Dashboard - Live metrics visualization
5. Slack/GitHub - Automated notifications

---

## 🐛 The Bug Explained (Visual)

```
Normal Operation:
Request → Acquire Conn → Query (50ms) → Release Conn → Response
         [50ms total]

With Bug Under Load:
Request → Acquire Conn → Query Fails → Sleep 1s → Retry Fails → Sleep 2s → Retry Fails → Sleep 4s → Release
         [7000ms holding connection!]

20 concurrent requests × 7s = Pool exhausted for 7 seconds
New requests timeout waiting for connections
```

---

## ✅ Pre-Demo Checklist

- [ ] FortressAI repo cloned
- [ ] Tests run successfully (19 passed)
- [ ] IncidentDNA services running (Snowflake, agents, dashboard)
- [ ] GitHub webhook configured
- [ ] Slack channel ready
- [ ] Demo mode enabled (`DEMO_MODE=true`)
- [ ] Talking points memorized
- [ ] Backup video recorded (just in case)

---

## 🎬 Demo Flow (2 minutes)

**0:00-0:20** - Show the feature and passing tests
**0:20-0:30** - Push to GitHub
**0:30-0:50** - Show Snowflake detection (35s)
**0:50-1:10** - Show agent investigation (Cortex Search)
**1:10-1:20** - Show auto-fix decision (confidence 92%)
**1:20-1:30** - Show fix execution and resolution
**1:30-2:00** - Show impact metrics and DNA storage

---

## 🔧 Troubleshooting

**Tests fail?**
```bash
pip install pytest
cd IncidentDNA/FortressAI
pytest tests/test_db_pool.py -v
```

**Push not detected?**
- Check `DEMO_MODE=true` in `.env`
- Verify GitHub webhook configured
- Check `trigger_listener.py` is running

**Agents not responding?**
- Check `agents/crew.py` is running
- Verify Snowflake connection
- Check `AI.ANOMALY_EVENTS` table

**Metrics not showing?**
- Check dashboard is running (`npm run dev`)
- Verify Snowflake dynamic tables refreshing
- Check `ANALYTICS.METRIC_DEVIATIONS` table

---

## 📞 Quick Commands

```bash
# Run tests
pytest tests/test_db_pool.py -v

# Push to GitHub
git push origin main

# Check Snowflake anomalies
snowsql -q "SELECT * FROM ANALYTICS.METRIC_DEVIATIONS WHERE service_name='broker'"

# Check agent decisions
snowsql -q "SELECT * FROM AI.DECISIONS ORDER BY created_at DESC LIMIT 5"

# Check incident history
snowsql -q "SELECT * FROM AI.INCIDENT_HISTORY ORDER BY resolved_at DESC LIMIT 1"

# Start dashboard
cd dashboard && npm run dev

# Start agents
python agents/crew.py

# Start trigger listener
python agents/trigger_listener.py
```

---

**🎉 You're ready! Break a leg!**
