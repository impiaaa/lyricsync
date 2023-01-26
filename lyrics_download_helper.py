import os
import json
import urllib.parse
import webbrowser

class PrivateMozilla(webbrowser.Mozilla):
    remote_action = "--private-window"

def caseInsensitive(dir, path):
    ls = os.listdir(dir)
    lowerLs = [f.casefold() for f in ls]
    return ls[lowerLs.index(path.casefold())]

browser = PrivateMozilla("firefox")

for line in open("has lyrics.txt"):
    line = line.rstrip()
    if (not os.path.exists(line)) or os.path.exists(os.path.join(line, "lyrics.txt")) or os.path.exists(os.path.join(line, "lyrics.srt")):
        print("skipping", line)
        continue
    print(line)
    info = json.load(open(os.path.join(line, caseInsensitive(line, "info.dat")), 'rb'))
    browser.open("https://www.google.com/search?q="+urllib.parse.quote_plus(info.get("_songAuthorName", info.get("_songSubName", info.get("_levelAuthorName", "")))+' '+info["_songName"]+' lyrics'))
    
    with open(os.path.join(line, "lyrics.txt"), 'w') as fout:
        while True:
            try:
                print(input(), file=fout)
            except EOFError:
                break

