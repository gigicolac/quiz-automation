#!/usr/bin/env bash
# Copy a quiz's thumbnails A and B to the `studio-thumbnails` branch, so YouTube Studio in the browser on
# Giulia's Mac can load them from raw.githubusercontent.com for the A/B test (Studio's page can't fetch
# release files, and the built-in browser has no file picker; 16 Nov 2026). Only thumbnail JPEGs go there.
# Usage: publish_studio_thumbnails.sh <quiz> <dir with <quiz>-thumbnail-a.jpg and -b.jpg>
set -euo pipefail
quiz="$1"; dir="$2"
case "$quiz" in ""|*/*|*..*) echo "bad quiz"; exit 1;; esac
work="$(mktemp -d)"
url="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
if git ls-remote --exit-code --heads "$url" studio-thumbnails >/dev/null 2>&1; then
  git clone -q --depth 1 --branch studio-thumbnails "$url" "$work"
else
  git init -q "$work"; git -C "$work" checkout -q --orphan studio-thumbnails; git -C "$work" remote add origin "$url"
fi
for v in a b; do cp "$dir/$quiz-thumbnail-$v.jpg" "$work/"; done
cd "$work"
git add "$quiz-thumbnail-a.jpg" "$quiz-thumbnail-b.jpg"
if git diff --cached --quiet; then echo "studio-thumbnails: $quiz unchanged"; exit 0; fi
git -c user.name="github-actions[bot]" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
  commit -q -m "Studio thumbnails for $quiz"
for i in 1 2 3; do
  git push -q origin HEAD:studio-thumbnails && { echo "studio-thumbnails: $quiz published"; exit 0; }
  git pull -q --rebase origin studio-thumbnails || true
done
echo "::warning::could not publish $quiz thumbnails to studio-thumbnails"
