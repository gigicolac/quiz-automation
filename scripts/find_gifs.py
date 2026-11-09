"""Find candidate GIFs (as MP4 URLs Canva can import) for each query in a quiz's gif_queries.json,
then pick one per slot into gifs_selected.json.

gif_queries.json is either a plain list of {"n", "question_query", "answer_query"} rows, or
{"allow_branded": true, "queries": [... rows, each optionally with "image_title"]}.

- GIPHY is used when GIPHY_API_KEY is set; Pixabay videos are the fallback when PIXABAY_API_KEY is set.
- By default branded/TV accounts in BLOCKED_USERS are skipped. "allow_branded": true (fandom quizzes,
  e.g. a Disney quiz where Giulia wants GIFs from the actual films) lifts that filter and prefers
  official studio accounts in PREFERRED_USERS.
- For fandom quizzes a GIF is only picked when its title mentions something from the query. When no
  GIF fits, a still image from the film is used instead (first frame of a GIF found by the row's
  "film" name, else the name in "image_title"), then the Wikipedia lead image of "image_title".
- A GIF is not reused for both the question and the answer of the same pair.
Writes gif_candidates.json and gifs_selected.json next to the queries file.
"""
import json, os, sys, urllib.parse, urllib.request

BLOCKED_TITLE_WORDS = ["friends", "simpsons", "spongebob", "breaking bad", "game of thrones", "trump", "beyonce", "salt bae", "south park", "netflix", "bbc", "red bull", "history", "general hospital", "pawn stars", "sea of thieves", "storybots", "galifianakis", "conan", "mr t", "beatles", "scarlett", "mia farrow", "horror", "movie", "season", "episode", "tv"]
BLOCKED_USERS = {"natgeowild", "southparkgifs", "natgeo", "netflix", "nbc", "foxsportsaus", "hbo", "disney", "warnerbros", "abcnetwork", "cbs", "bbc", "bbcamerica", "bbcearth", "thesimpsons", "spongebob", "redbull", "generalhospital", "historylat", "historyuk", "seaofthieves", "storybots", "teamcoco", "netflixlat", "dazn", "outbacksteakhouse", "friends", "southpark", "lifetimetv", "adweek", "fuckthatsdelicious", "nowthis", "pri", "worldcup", "worldrugby"}
# never wanted, even for fandom quizzes
ALWAYS_BLOCKED_TITLE_WORDS = ["trump", "horror"]
PREFERRED_USERS = {"disney", "pixar", "disneyanimation", "disneystudios", "disneyplus", "disneyjunior", "disneychannel", "disneypixar", "waltdisneystudios", "disneyparks"}
UA = {"User-Agent": "quiz-automation-gif-finder/1.0"}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def giphy(q, key, branded=False):
    u = "https://api.giphy.com/v1/gifs/search?" + urllib.parse.urlencode({"api_key": key, "q": q, "limit": 25, "rating": "g", "lang": "en"})
    out = []
    for g in get(u).get("data", []):
        user = (g.get("username") or "").lower()
        title = (g.get("title") or "").lower()
        if any(w in title for w in ALWAYS_BLOCKED_TITLE_WORDS):
            continue
        if not branded and (user in BLOCKED_USERS or any(w in title for w in BLOCKED_TITLE_WORDS)):
            continue
        imgs = g.get("images", {})
        mp4 = imgs.get("original", {}).get("mp4")
        if mp4:
            out.append({"source": "giphy", "type": "gif", "id": g["id"], "user": user, "title": g.get("title", ""),
                        "mp4": mp4.split("?")[0], "clean_mp4": f"https://media.giphy.com/media/{g['id']}/giphy.mp4",
                        "still": (imgs.get("original_still", {}).get("url") or "").split("?")[0]})
    if branded:  # best title match first, official studio accounts break ties, then GIPHY's order
        out.sort(key=lambda c: -score(q, c))
    return out[:8]


STOP = {"the", "and", "of", "a", "an", "in", "gif", "by", "disney", "pixar", "film", "movie", "animation"}


def words(text):
    ws = "".join(ch if ch.isalnum() else " " for ch in text.lower()).split()
    return {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in ws if len(w) > 2 and w not in STOP}


def score(q, c):
    """2 per query word found in the GIF title, +1 for an official studio account."""
    return 2 * len(words(q) & words(c.get("title", ""))) + (c.get("user") in PREFERRED_USERS)


def pixabay(q, key):
    u = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": key, "q": q, "per_page": 5, "safesearch": "true"})
    out = []
    for h in get(u).get("hits", [])[:3]:
        v = h["videos"].get("small") or h["videos"].get("tiny")
        out.append({"source": "pixabay", "type": "gif", "id": h["id"], "user": h.get("user", ""), "title": h.get("tags", ""), "mp4": v["url"]})
    return out


def wiki_image(title):
    u = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "prop": "pageimages", "piprop": "original", "titles": title, "redirects": 1, "format": "json"})
    for page in get(u).get("query", {}).get("pages", {}).values():
        src = page.get("original", {}).get("source")
        if src:
            return {"source": "wikipedia", "type": "image", "id": page.get("pageid"), "title": page.get("title", title), "url": src}
    return None


def pick(cands, avoid, q, strict):
    """First unused candidate; with strict, its title must mention something from the query."""
    for c in cands:
        if c.get("id") in avoid:
            continue
        if strict and not (words(q) & words(c.get("title", ""))):
            continue
        return c
    return None


def still_image(film, key, avoid):
    """A still frame from the actual film: the first frame of the best GIF for the film's name."""
    for c in giphy(film, key, branded=True):
        if c.get("id") not in avoid and c.get("still") and words(film) & words(c.get("title", "")):
            return {"source": "giphy_still", "type": "image", "id": c["id"], "user": c["user"],
                    "title": c["title"], "url": c["still"]}
    return None


def main(path):
    gk, pk = os.environ.get("GIPHY_API_KEY"), os.environ.get("PIXABAY_API_KEY")
    print("GIPHY key set:", bool(gk), "| Pixabay key set:", bool(pk))
    if not (gk or pk):
        sys.exit("No GIF API key available")
    spec = json.load(open(path))
    branded = isinstance(spec, dict) and spec.get("allow_branded", False)
    queries = spec["queries"] if isinstance(spec, dict) else spec
    cache, result, selected = {}, [], []
    for row in queries:
        entry, sel, used = {"n": row["n"]}, {"n": row["n"]}, set()
        for field in ("question_query", "answer_query"):
            q = row[field]
            if q not in cache:
                c = []
                try:
                    if gk: c = giphy(q, gk, branded)
                    if not c and pk and not branded: c = pixabay(q, pk)
                except Exception as e:
                    print("error", q, e)
                cache[q] = c
            slot = field.replace("_query", "_gif")
            entry[field] = q
            entry[field.replace("query", "candidates")] = cache[q]
            choice = pick(cache[q], used, q, strict=branded)
            film = row.get("film") or (row.get("image_title") or "").split(" (")[0]
            if not choice and branded and film and gk:
                try:
                    choice = still_image(film, gk, used)
                except Exception as e:
                    print("error still", film, e)
            if not choice and row.get("image_title"):
                try:
                    choice = wiki_image(row["image_title"])
                except Exception as e:
                    print("error image", row["image_title"], e)
            if choice:
                used.add(choice.get("id"))
                sel[slot] = choice
        result.append(entry)
        selected.append(sel)
        print(row["n"], {k: len(v) for k, v in entry.items() if k.endswith("candidates")},
              {k: v["type"] for k, v in sel.items() if k != "n"})
    d = os.path.dirname(path)
    json.dump(result, open(os.path.join(d, "gif_candidates.json"), "w"), indent=1)
    json.dump(selected, open(os.path.join(d, "gifs_selected.json"), "w"), indent=1)
    missing = [s["n"] for s in selected if not ("question_gif" in s and "answer_gif" in s)]
    if missing:
        print("::warning::No GIF or image for questions", missing)


if __name__ == "__main__":
    main(sys.argv[1])
