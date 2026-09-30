"""Builds data.json: 0.5-PPR points per game (nflverse), rookie draft picks, and
FantasyCalc dynasty market values, all keyed by Sleeper player id."""
import datetime, json
import nfl_data_py as nfl
import requests

yr = datetime.date.today().year
ids = nfl.import_ids()[["gsis_id", "sleeper_id"]].dropna()
g2s = {g: str(int(float(s))) for g, s in zip(ids.gsis_id, ids.sleeper_id)}

# Blend last season (weight 1) and this season (weight 1.5)
acc = {}
for season, w in ((yr - 1, 1.0), (yr, 1.5)):
    try:
        wk = nfl.import_weekly_data([season])
    except Exception as e:
        print("skip", season, e)
        continue
    if "season_type" in wk:
        wk = wk[wk.season_type == "REG"]
    wk = wk.assign(p=wk.fantasy_points_ppr - 0.5 * wk.receptions)
    for pid, g in wk.groupby("player_id"):
        a = acc.setdefault(pid, [0.0, 0.0])
        a[0] += w * g.p.sum()
        a[1] += w * len(g)

players = {}
for gsis, (pts, games) in acc.items():
    sid = g2s.get(gsis)
    if sid and games >= 6:
        players[sid] = {"ppg": round(pts / games, 2)}

# Rookie draft position (overall pick)
try:
    dp = nfl.import_draft_picks([yr])
    for gsis, pick in zip(dp.gsis_id, dp.pick):
        sid = g2s.get(gsis)
        if sid:
            players.setdefault(sid, {})["pick"] = int(pick)
except Exception as e:
    print("draft picks skipped", e)

# Market values (12-team superflex, 0.5 PPR)
try:
    r = requests.get("https://api.fantasycalc.com/values/current",
                     params={"isDynasty": "true", "numQbs": 2, "numTeams": 12, "ppr": 0.5}, timeout=30)
    for x in r.json():
        sid = str(x["player"].get("sleeperId"))
        if sid != "None":
            players.setdefault(sid, {})["mv"] = x["value"]
except Exception as e:
    print("market values skipped", e)

json.dump({"updated": datetime.date.today().isoformat(), "players": players}, open("data.json", "w"))
print(len(players), "players written")
