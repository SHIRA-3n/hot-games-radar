import os, requests
from dotenv import load_dotenv     # ★ 追加
load_dotenv()                      # ★ 追加

STEAM_KEY = os.getenv("STEAM_API_KEY")
URL = "https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/"

def steam_ccu(appid: int) -> int:
    if not STEAM_KEY:
        return 0
    try:
        r = requests.get(URL, params={"key": STEAM_KEY, "appid": appid}, timeout=5)
        return r.json().get("response", {}).get("player_count", 0)
    except Exception:
        return 0
