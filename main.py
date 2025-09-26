import requests
from bs4 import BeautifulSoup
from pushbullet import Pushbullet
from flask import Flask
import threading
from threading import Thread
import re
import time
import string
import os

API_KEY = os.getenv("PUSHBULLET_API_KEY")

pb = Pushbullet(API_KEY)

last_push_id = None

app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# Start keep-alive web server
keep_alive()

# URL of the page to scrape
raw_url="https://www.vlr.gg/542266/team-heretics-vs-mibr-valorant-champions-2025-ubqf"

# Keep only valid URL characters (letters, numbers, :, /, ., ?, =, &, %, -)
#url = re.sub(r"[^\w:/.?&=-%]", "", raw_url)
url = "".join(c for c in raw_url if c in string.printable)

url = url.strip()

previous_scores = None

def check():
    global previous_scores, last_push_id
    while True:
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
    
            # --- Team names ---
            teams = soup.select(".match-header-link .wf-title-med")
            team1 = teams[0].text.strip() if len(teams) > 0 else "Team1"
            team2 = teams[1].text.strip() if len(teams) > 1 else "Team2"
    
            # --- Match header score ---
            header_scores = [
                s.text.strip()
                for s in soup.select("div.match-header-vs-score .js-spoiler span")
                if s.text.strip().isdigit()
            ]
    
            # --- Map names (cleaned) ---
            raw_map_names = soup.select(".vm-stats-game-header .map")
            map_names = []
            for m in raw_map_names:
                # only take the first word (the map name like Bind/Haven)
                clean = m.text.strip().split()[0]
                map_names.append(clean)
    
            # --- Map scores ---
            scores_all = [
                d.text.strip() for d in soup.find_all("div", class_="score")
            ]
            map_scores = [
                scores_all[i] + " " + scores_all[i + 1]
                for i in range(0, len(scores_all), 2)
            ]
    
            # Build snapshot
            current_scores = [team1, team2] + header_scores + map_scores
    
            # Print and notify only if something changed
            if current_scores != previous_scores:
                if last_push_id:
                    try:
                        pb.delete_push(last_push_id)
                    except Exception as e:
                        pass
                # Build header
                header = f"{team1} vs {team2}\nMatch Score: {' '.join(header_scores)}"
    
                # Build map scores text
                maps_text = ""
                for idx, score in enumerate(map_scores, start=1):
                    map_name = map_names[idx - 1] if idx - 1 < len(
                        map_names) else "Unknown"
                    maps_text += f"Map {idx} ({map_name}): {score}\n"
    
                # Print to terminal
                print(header)
                print(maps_text)
    
                push = pb.push_note(title=header, body=maps_text)
                last_push_id = push.get("iden")
                previous_scores = current_scores
    
        except Exception as e:
            print("Error fetching data:", e)
    
        time.sleep(5)  # wait 5 seconds before refreshing

if __name__ == "__main__":
    # Start Flask (keep-alive server)
    Thread(target=run_flask).start()
    # Start scraper loop
    Thread(target=check).start()
