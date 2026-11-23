#!/usr/bin/env python3
"""Channel numbers for the weekly report and the GUMA forecast model (Giulia, 23 Nov 2026).

Writes reports/channel-stats.json from the YouTube Data and Analytics APIs (scope yt-analytics.readonly):
- channel totals now (subscribers, views, videos)
- by month: views, watch hours, subscribers gained/lost/net, subscribers at month end, watch hours in the
  12 months to month end, and thumbnail impressions and click-through rate when the API offers them
- by week (Monday to Sunday, the 6 most recent complete weeks): the same, with the change against the week before

Analytics days are US Pacific dates and lag 1-3 days. Env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
"""
import datetime as dt
import json
import sys
import urllib.error
import urllib.parse
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import upload_youtube as up  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"
BASE = ["views", "estimatedMinutesWatched", "subscribersGained", "subscribersLost"]
CTR = ["videoThumbnailImpressions", "videoThumbnailImpressionsClickRate"]
START = dt.date(2025, 11, 1)  # 12 months before the forecast model's first month (Oct 2026) and earlier


def report(token, start, end, metrics, dimension):
    q = urllib.parse.urlencode({"ids": "channel==MINE", "startDate": start.isoformat(), "endDate": end.isoformat(),
                                "metrics": ",".join(metrics), "dimensions": dimension, "sort": dimension})
    _, _, r = up.http("GET", f"{ANALYTICS}?{q}", token)
    cols = [h["name"] for h in r.get("columnHeaders", [])]
    return [dict(zip(cols, row)) for row in r.get("rows", [])]


def try_report(token, start, end, metrics, dimension):
    try:
        return report(token, start, end, metrics, dimension), None
    except (SystemExit, urllib.error.HTTPError, RuntimeError) as e:  # metric not offered for this channel/API
        return [], str(e)[:300]


def summarise(rows):
    views = sum(int(r.get("views", 0)) for r in rows)
    mins = sum(float(r.get("estimatedMinutesWatched", 0)) for r in rows)
    gained = sum(int(r.get("subscribersGained", 0)) for r in rows)
    lost = sum(int(r.get("subscribersLost", 0)) for r in rows)
    out = {"views": views, "watch_hours": round(mins / 60, 1), "subs_gained": gained, "subs_lost": lost,
           "subs_net": gained - lost}
    imp = sum(int(r.get("videoThumbnailImpressions", 0)) for r in rows)
    if imp:
        clicks = sum(int(r.get("videoThumbnailImpressions", 0)) * float(r.get("videoThumbnailImpressionsClickRate", 0))
                     for r in rows)
        out["impressions"] = imp
        out["ctr"] = round(clicks / imp, 4) if clicks > 1 else round(clicks / imp, 6)
    return out


def month_end(key):
    y, m = map(int, key.split("-"))
    return dt.date(y + m // 12, m % 12 + 1, 1) - dt.timedelta(days=1)


def target_at(day, targets):
    """Target subscribers and 12-month watch hours on `day`, straight-line between the month-end targets
    (config/targets.json). None before the first month or after the last."""
    pts = sorted((month_end(k), v) for k, v in targets.get("months", {}).items())
    for (d0, v0), (d1, v1) in zip(pts, pts[1:]):
        if d0 <= day <= d1:
            f = (day - d0).days / (d1 - d0).days
            return {k: round(v0[k] + f * (v1[k] - v0[k]), 1) for k in ("subs", "watch_hours_12m")}
    return None


def main():
    token = up.access_token()
    _, _, ch = up.http("GET", f"{up.API}/channels?part=statistics,snippet&mine=true", token)
    item = ch["items"][0]
    stats = item["statistics"]
    subs_now = int(stats.get("subscriberCount", 0))
    end = dt.date.today() - dt.timedelta(days=1)

    days = report(token, START, end, BASE, "day")
    ctr_days, ctr_error = try_report(token, START, end, CTR, "day")
    by_day = OrderedDict((r["day"], dict(r)) for r in days)
    for r in ctr_days:
        by_day.setdefault(r["day"], {"day": r["day"]}).update(r)
    rows = list(by_day.values())

    # months
    months = OrderedDict()
    for r in rows:
        months.setdefault(r["day"][:7], []).append(r)
    month_out = OrderedDict((m, summarise(rs)) for m, rs in months.items())
    # subscribers at each month end, counted back from today's total
    net_after = 0
    for m in reversed(list(month_out)):
        month_out[m]["subs_at_end"] = subs_now - net_after
        net_after += month_out[m]["subs_net"]
    keys = list(month_out)
    for i, m in enumerate(keys):
        month_out[m]["watch_hours_12m"] = round(sum(month_out[k]["watch_hours"] for k in keys[max(0, i - 11):i + 1]), 1)
        month_out[m]["complete"] = m < end.strftime("%Y-%m") or (end + dt.timedelta(days=1)).day == 1

    # weeks, Monday to Sunday, complete only
    last_sunday = end - dt.timedelta(days=(end.weekday() + 1) % 7)
    weeks = []
    for w in range(6, 0, -1):
        s = last_sunday - dt.timedelta(days=7 * w - 1)
        e = s + dt.timedelta(days=6)
        rs = [r for r in rows if s.isoformat() <= r["day"] <= e.isoformat()]
        weeks.append({"week": f"{s.isoformat()} to {e.isoformat()}", **summarise(rs)})
    for i in range(1, len(weeks)):
        for k in ("views", "watch_hours", "subs_net", "ctr"):
            if k in weeks[i] and k in weeks[i - 1]:
                weeks[i][f"{k}_change"] = round(weeks[i][k] - weeks[i - 1][k], 4)
    for wk in weeks:
        wk["subs_at_end"] = subs_now - sum(int(r.get("subscribersGained", 0)) - int(r.get("subscribersLost", 0))
                                                     for r in rows if r["day"] > wk["week"][-10:])
    tpath = ROOT / "config" / "targets.json"
    targets = json.loads(tpath.read_text()) if tpath.exists() else {}
    for wk in weeks:
        e = dt.date.fromisoformat(wk["week"][-10:])
        wk["watch_hours_12m_at_end"] = round(sum(float(r.get("estimatedMinutesWatched", 0)) for r in rows
                                                 if (e - dt.timedelta(days=364)).isoformat() <= r["day"] <= e.isoformat()) / 60, 1)
        t = target_at(e, targets)
        if t:
            wk["target_subs"], wk["target_watch_hours_12m"] = t["subs"], t["watch_hours_12m"]
        if targets.get("ctr"):
            wk["target_ctr"] = targets["ctr"]
    out = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "channel": {"title": item["snippet"]["title"], "subscribers": subs_now,
                       "views": int(stats.get("viewCount", 0)), "videos": int(stats.get("videoCount", 0))},
           "data_to": end.isoformat(), "ctr_error": ctr_error, "months": month_out, "weeks": weeks}
    p = ROOT / "reports" / "channel-stats.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
