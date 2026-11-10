#!/usr/bin/env bash
# Installs the thumbnail fonts used by scripts/make_thumbnails.py (the original Canva thumbnail's fonts):
#   Nunito Sans Bold  (series name and hook line)
#   Tinos Italic      ("Quiz #n"; free metric-compatible twin of Times New Roman Italic, which Canva used)
# Both are open-licence Google fonts, taken as static .ttf files from pinned npm packages.
set -euo pipefail
dest=/usr/share/fonts/truetype/google-fonts
tmp=$(mktemp -d)
( cd "$tmp" && npm pack -q @expo-google-fonts/nunito-sans@0.4.2 @expo-google-fonts/tinos@0.4.2 >/dev/null
  for f in *.tgz; do mkdir "${f%.tgz}" && tar xzf "$f" -C "${f%.tgz}"; done )
sudo mkdir -p "$dest"
sudo cp "$tmp"/expo-google-fonts-nunito-sans-0.4.2/package/700Bold/NunitoSans_700Bold.ttf "$dest/NunitoSans-Bold.ttf"
sudo cp "$tmp"/expo-google-fonts-tinos-0.4.2/package/400Regular_Italic/Tinos_400Regular_Italic.ttf "$dest/Tinos-Italic.ttf"
rm -rf "$tmp"
ls -l "$dest/NunitoSans-Bold.ttf" "$dest/Tinos-Italic.ttf"
