"""Find candidate GIFs (as MP4 URLs Canva can import) for each query in a quiz's gif_queries.json.

GIPHY is used when GIPHY_API_KEY is set; Pixabay videos are the fallback when PIXABAY_API_KEY is set.
Branded/watermarked GIPHY accounts in BLOCKED_USERS are skipped.
Writes gif_candidates.json next to the queries file.
"""
import json, os, sys, urllib.parse, urllib.request

BLOCKED_TITLE_WORDS = ["friends", "simpsons", "spongebob", "breaking bad", "game of thrones", "trump", "beyonce", "salt bae", "south park", "netflix", "bbc", "red bull", "history", "general hospital", "pawn stars", "sea of thieves", "storybots", "galifianakis", "conan", "mr t", "beatles", "scarlett", "mia farrow", "horror", "movie", "season", "episode", "tv"]
BLOCKED_USERS = {"natgeowild", "southparkgifs", "natgeo", "netflix", "nbc", "foxsportsaus", "hbo", "disney", "warnerbros", "abcnetwork", "cbs", "bbc", "bbcamerica", "bbcearth", "thesimpsons", "spongebob", "redbull", "generalhospital", "historylat", "historyuk", "seaofthieves", "storybots", "teamcoco", "netflixlat", "dazn", "outbacksteakhouse", "friends", "southpark", "lifetimetv", "adweek", "fuckthatsdelicious", "nowthis", "pri", "worldcup", "worldrugby"}

def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)

def giphy(q, key):
    u = "https://api.giphy.com/v1/gifs/search?" + urllib.parse.urlencode({"api_key": key, "q": q, "limit": 25, "rating": "g", "lang": "en"})
    out = []
    for g in get(u).get("data", []):
        user = (g.get("username") or "").lower()
        title = (g.get("title") or "").lower()
        if user in BLOCKED_USERS or any(w in title for w in BLOCKED_TITLE_WORDS):
            continue
        mp4 = g.get("images", {}).get("original", {}).get("mp4")
        if mp4:
            out.append({"source": "giphy", "id": g["id"], "user": user, "title": g.get("title", ""), "mp4": mp4.split("?")[0]})
        if len(out) >= 5:
            break
    return out

def pixabay(q, key):
    u = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": key, "q": q, "per_page": 5, "safesearch": "true"})
    out = []
    for h in get(u).get("hits", [])[:3]:
        v = h["videos"].get("small") or h["videos"].get("tiny")
        out.append({"source": "pixabay", "id": h["id"], "user": h.get("user", ""), "title": h.get("tags", ""), "mp4": v["url"]})
    return out

def main(path):
    gk, pk = os.environ.get("GIPHY_API_KEY"), os.environ.get("PIXABAY_API_KEY")
    print("GIPHY key set:", bool(gk), "| Pixabay key set:", bool(pk))
    if not (gk or pk):
        sys.exit("No GIF API key available")
    queries = json.load(open(path))
    cache, result = {}, []
    for row in queries:
        entry = {"n": row["n"]}
        for field in ("question_query", "answer_query"):
            q = row[field]
            if q not in cache:
                c = []
                try:
                    if gk: c = giphy(q, gk)
                    if not c and pk: c = pixabay(q, pk)
                except Exception as e:
                    print("error", q, e)
                cache[q] = c
            entry[field] = q
            entry[field.replace("query", "candidates")] = cache[q]
        result.append(entry)
        print(row["n"], {k: len(v) for k, v in entry.items() if k.endswith("candidates")})
    json.dump(result, open(os.path.join(os.path.dirname(path), "gif_candidates.json"), "w"), indent=1)

if __name__ == "__main__":
    main(sys.argv[1])
