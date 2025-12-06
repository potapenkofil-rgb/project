import os
import sys
import time
import json
import requests
from datetime import datetime, timedelta
from tabulate import tabulate
from math import exp

API_KEY = "1f3ae34bfd659531653ae3067c1e0676"
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}
LEAGUE_ID = 39
SEASON = 2023
CACHE_DIR = ".cache_football"
TEAMS_CACHE = os.path.join(CACHE_DIR, "teams.json")
MATCHES_CACHE = os.path.join(CACHE_DIR, "matches.json")
CACHE_TTL_HOURS = 24

def ensure_cache_dir():
    os.makedirs(CACHE_DIR, exist_ok=True)

def cache_is_fresh(path):
    if not os.path.exists(path):
        return False
    age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(path))
    return age < timedelta(hours=CACHE_TTL_HOURS)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def human_date(iso):
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return iso

class FootballAPI:
    def __init__(self, api_key):
        if not api_key:
            raise RuntimeError("API key отсутствует. Установи переменную окружения FOOTBALL_API_KEY.")
        self.headers = {"x-apisports-key": api_key}

    def get_teams(self, league=LEAGUE_ID, season=SEASON):
        url = f"{BASE_URL}/teams"
        params = {"league": league, "season": season}
        r = requests.get(url, headers=self.headers, params=params, timeout=20)
        r.raise_for_status()
        return r.json().get("response", [])

    def get_fixtures(self, league=LEAGUE_ID, season=SEASON):
        url = f"{BASE_URL}/fixtures"
        params = {"league": league, "season": season}
        r = requests.get(url, headers=self.headers, params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("response", [])

class FootballAnalyzer:
    def __init__(self, teams_raw, matches_raw):
        self.teams = {}
        self.team_ids = {}
        for t in teams_raw:
            tid = t["team"]["id"]
            name = t["team"]["name"]
            self.teams[tid] = name
            self.team_ids[name] = tid

        self.matches = matches_raw
        self.team_matches = {tid: [] for tid in self.teams.keys()}
        for m in self.matches:
            home = m["teams"]["home"]["id"]
            away = m["teams"]["away"]["id"]
            if home in self.team_matches:
                self.team_matches[home].append(m)
            if away in self.team_matches:
                self.team_matches[away].append(m)
        for tid in self.team_matches:
            self.team_matches[tid].sort(key=lambda x: x["fixture"]["date"], reverse=True)

    def get_recent_matches(self, team_id, count=5):
        return self.team_matches.get(team_id, [])[:count]

    def compute_standings(self):
        table = {}
        for tid in self.teams.keys():
            table[tid] = {"played":0,"wins":0,"draws":0,"losses":0,"gf":0,"ga":0,"points":0}
        for m in self.matches:
            status = m.get("fixture", {}).get("status", {}).get("short", "")
            finished = status in ("FT","AET","PEN") or (m.get("goals",{}).get("home") is not None and m.get("goals",{}).get("away") is not None)
            if not finished:
                continue
            home = m["teams"]["home"]["id"]
            away = m["teams"]["away"]["id"]
            gh = m["goals"]["home"] if m["goals"]["home"] is not None else 0
            ga = m["goals"]["away"] if m["goals"]["away"] is not None else 0
            table[home]["played"] += 1
            table[away]["played"] += 1
            table[home]["gf"] += gh
            table[home]["ga"] += ga
            table[away]["gf"] += ga
            table[away]["ga"] += gh
            if gh > ga:
                table[home]["wins"] += 1
                table[away]["losses"] += 1
                table[home]["points"] += 3
            elif gh < ga:
                table[away]["wins"] += 1
                table[home]["losses"] += 1
                table[away]["points"] += 3
            else:
                table[home]["draws"] += 1
                table[away]["draws"] += 1
                table[home]["points"] += 1
                table[away]["points"] += 1
        rows = []
        for tid, stats in table.items():
            gd = stats["gf"] - stats["ga"]
            rows.append({"team_id": tid,"team": self.teams[tid], **stats,"gd": gd})
        rows.sort(key=lambda r: (r["points"], r["gd"], r["gf"]), reverse=True)
        return rows

    def compute_team_metrics(self, team_id):
        matches = [m for m in self.team_matches.get(team_id, []) if m.get("goals",{}).get("home") is not None and m.get("goals",{}).get("away") is not None]
        mp = len(matches)
        gf = ga = 0
        for m in matches:
            if m["teams"]["home"]["id"] == team_id:
                gf += m["goals"]["home"] if m["goals"]["home"] is not None else 0
                ga += m["goals"]["away"] if m["goals"]["away"] is not None else 0
            else:
                gf += m["goals"]["away"] if m["goals"]["away"] is not None else 0
                ga += m["goals"]["home"] if m["goals"]["home"] is not None else 0
        avg_gf = gf / mp if mp else 0.0
        avg_ga = ga / mp if mp else 0.0
        attack = avg_gf
        defense = 1 / (avg_ga + 0.1)
        recent = self.get_recent_matches(team_id, count=5)
        points_recent = 0
        for m in recent:
            gh = m["goals"]["home"]
            ga_ = m["goals"]["away"]
            if gh is None or ga_ is None:
                continue
            if m["teams"]["home"]["id"] == team_id:
                if gh > ga_:
                    points_recent += 3
                elif gh == ga_:
                    points_recent += 1
            else:
                if ga_ > gh:
                    points_recent += 3
                elif ga_ == gh:
                    points_recent += 1
        form = points_recent / 15
        return {"matches_played": mp,"avg_gf": avg_gf,"avg_ga": avg_ga,"attack": attack,"defense": defense,"form": form,"recent_points": points_recent}

    def rating(self, metrics):
        attack_score = metrics["attack"]
        defense_score = metrics["defense"] * 0.5
        form_score = metrics["form"] * 3
        rating = attack_score * 0.6 + defense_score * 0.3 + form_score * 0.1
        return rating

    def compare(self, team_a_id, team_b_id):
        ma = self.compute_team_metrics(team_a_id)
        mb = self.compute_team_metrics(team_b_id)
        ra = self.rating(ma)
        rb = self.rating(mb)
        exp_a = exp(ra)
        exp_b = exp(rb)
        pa = exp_a / (exp_a + exp_b)
        pb = exp_b / (exp_a + exp_b)
        return {"team_a": self.teams[team_a_id],"team_b": self.teams[team_b_id],"rating_a": ra,"rating_b": rb,"prob_a": pa * 100,"prob_b": pb * 100,"metrics_a": ma,"metrics_b": mb}

def print_standings(table_rows):
    headers = ["#", "Team", "P", "W", "D", "L", "GF", "GA", "GD", "Pts"]
    lines = []
    for i, r in enumerate(table_rows, start=1):
        lines.append([i, r["team"], r["played"], r["wins"], r["draws"], r["losses"], r["gf"], r["ga"], r["gd"], r["points"]])
    print(tabulate(lines, headers=headers, tablefmt="pretty"))

def print_team_metrics(name, metrics):
    print(f"\n--- Статистика {name} ---")
    print(f"Матчей сыграно: {metrics['matches_played']}")
    print(f"Средние забитые: {metrics['avg_gf']:.2f}")
    print(f"Средние пропущенные: {metrics['avg_ga']:.2f}")
    print(f"Атака (attack score): {metrics['attack']:.3f}")
    print(f"Защита (defense score): {metrics['defense']:.3f}")
    print(f"Форма (последние 5 матчей, 0..1): {metrics['form']:.2f} (очки: {metrics['recent_points']})")
    print("--------------------------\n")

def main():
    print("Football Outcome Analyzer — консоль (FULL).")
    if not API_KEY:
        print("Ошибка: API ключ не найден. Установи переменную окружения FOOTBALL_API_KEY.")
        return
    ensure_cache_dir()
    api = FootballAPI(API_KEY)
    if cache_is_fresh(TEAMS_CACHE):
        teams_raw = load_json(TEAMS_CACHE)
        print("Загружено команды из кеша.")
    else:
        print("Запрос команд к API...")
        teams_raw = api.get_teams()
        save_json(TEAMS_CACHE, teams_raw)
        print("Команды сохранены в кеш.")
    if cache_is_fresh(MATCHES_CACHE):
        matches_raw = load_json(MATCHES_CACHE)
        print("Загружено матчи из кеша.")
    else:
        print("Запрос всех матчей лиги к API (один запрос)...")
        matches_raw = api.get_fixtures()
        save_json(MATCHES_CACHE, matches_raw)
        print("Матчи сохранены в кеш.")
    analyzer = FootballAnalyzer(teams_raw, matches_raw)
    team_list = list(analyzer.team_ids.keys())
    while True:
        print("\nГлавное меню:")
        print("1) Показать таблицу АПЛ (по загруженным матчам)")
        print("2) Показать статистику команды")
        print("3) Сравнить две команды (вероятности)")
        print("4) Обновить кеш (force refresh)")
        print("5) Экспортить турнирную таблицу в CSV")
        print("6) Выход")
        choice = input("> ").strip()
        if choice == "1":
            table = analyzer.compute_standings()
            print_standings(table)
        elif choice == "2":
            print("Выбери команду:")
            for i, name in enumerate(team_list, start=1):
                print(f"{i}. {name}")
            idx = input("Номер команды: ").strip()
            if not idx.isdigit() or not (1 <= int(idx) <= len(team_list)):
                print("Неверно.")
                continue
            name = team_list[int(idx)-1]
            tid = analyzer.team_ids[name]
            metrics = analyzer.compute_team_metrics(tid)
            print_team_metrics(name, metrics)
            recent = analyzer.get_recent_matches(tid, count=5)
            print("Последние матчи (новые->старые):")
            for m in recent:
                date = human_date(m["fixture"]["date"])
                h = m["teams"]["home"]["name"]
                a = m["teams"]["away"]["name"]
                gh = m["goals"]["home"]
                ga = m["goals"]["away"]
                print(f"{date} | {h} {gh}:{ga} {a}")
        elif choice == "3":
            print("Выбери первую команду:")
            for i, name in enumerate(team_list, start=1):
                print(f"{i}. {name}")
            a = input("№ команды A: ").strip()
            b = input("№ команды B: ").strip()
            if not (a.isdigit() and b.isdigit()):
                print("Неверный ввод.")
                continue
            ia, ib = int(a)-1, int(b)-1
            if ia==ib or ia<0 or ib<0 or ia>=len(team_list) or ib>=len(team_list):
                print("Неверный выбор команд.")
                continue
            ta = team_list[ia]
            tb = team_list[ib]
            ra = analyzer.compare(analyzer.team_ids[ta], analyzer.team_ids[tb])
            print(f"\nСравнение: {ta} vs {tb}")
            print(f"{ta} — рейтинг {ra['rating_a']:.4f}, вероятность победы: {ra['prob_a']:.2f}%")
            print(f"{tb} — рейтинг {ra['rating_b']:.4f}, вероятность победы: {ra['prob_b']:.2f}%")
            print("\n-- Детальные метрики --")
            print_team_metrics(ta, ra["metrics_a"])
            print_team_metrics(tb, ra["metrics_b"])
        elif choice == "4":
            print("Обновляю кеш данных с API...")
            teams_raw = api.get_teams()
            save_json(TEAMS_CACHE, teams_raw)
            matches_raw = api.get_fixtures()
            save_json(MATCHES_CACHE, matches_raw)
            analyzer = FootballAnalyzer(teams_raw, matches_raw)
            team_list = list(analyzer.team_ids.keys())
            print("Кеш обновлён.")
        elif choice == "5":
            table = analyzer.compute_standings()
            csv_path = os.path.join(CACHE_DIR, "standings.csv")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write("position,team,played,wins,draws,losses,gf,ga,gd,points\n")
                for pos, r in enumerate(table, start=1):
                    f.write(f"{pos},{r['team']},{r['played']},{r['wins']},{r['draws']},{r['losses']},{r['gf']},{r['ga']},{r['gd']},{r['points']}\n")
            print(f"Турнирная таблица экспортирована в {csv_path}")
        elif choice == "6":
            print("Выход...")
            break
        else:
            print("Неверный ввод")

if __name__ == "__main__":
    main()
