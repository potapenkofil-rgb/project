import logging
from math import exp
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

API_KEY_FOOTBALL = "1f3ae34bfd659531653ae3067c1e0676"
BASE_URL = "https://v3.football.api-sports.io"
LEAGUE_ID = 39
SEASON = 2023
TOKEN = "8567118839:AAHSRNSlZU17mj5H9Tq-lD5kiIamGl7EecI"

logging.basicConfig(level=logging.WARNING)

class FootballAPI:
    def __init__(self, api_key):
        self.headers = {"x-apisports-key": api_key}

    def get_teams(self):
        r = requests.get(
            f"{BASE_URL}/teams",
            headers=self.headers,
            params={"league": LEAGUE_ID, "season": SEASON},
            timeout=20
        )
        r.raise_for_status()
        return r.json()["response"]

    def get_fixtures(self):
        r = requests.get(
            f"{BASE_URL}/fixtures",
            headers=self.headers,
            params={"league": LEAGUE_ID, "season": SEASON},
            timeout=30
        )
        r.raise_for_status()
        return r.json()["response"]

class FootballAnalyzer:
    def __init__(self, api):
        self.api = api
        self.teams_raw = api.get_teams()
        self.matches_raw = api.get_fixtures()
        self.teams = {t["team"]["id"]: t["team"]["name"] for t in self.teams_raw}
        self.team_matches = {tid: [] for tid in self.teams}

        for m in self.matches_raw:
            h = m["teams"]["home"]["id"]
            a = m["teams"]["away"]["id"]
            if h in self.team_matches:
                self.team_matches[h].append(m)
            if a in self.team_matches:
                self.team_matches[a].append(m)

        for tid in self.team_matches:
            self.team_matches[tid].sort(key=lambda x: x["fixture"]["date"], reverse=True)

    def compute_team_metrics(self, team_id):
        matches = [m for m in self.team_matches[team_id] if m["goals"]["home"] is not None]
        mp = len(matches)
        gf = ga = wins = draws = losses = 0

        for m in matches:
            gh = m["goals"]["home"]
            ga_ = m["goals"]["away"]
            home = m["teams"]["home"]["id"]

            if team_id == home:
                gf += gh
                ga += ga_
                if gh > ga_:
                    wins += 1
                elif gh == ga_:
                    draws += 1
                else:
                    losses += 1
            else:
                gf += ga_
                ga += gh
                if ga_ > gh:
                    wins += 1
                elif ga_ == gh:
                    draws += 1
                else:
                    losses += 1

        avg_gf = gf / mp if mp else 0
        avg_ga = ga / mp if mp else 0
        form_points = 0
        for m in matches[:5]:
            gh = m["goals"]["home"]
            ga_ = m["goals"]["away"]
            if m["teams"]["home"]["id"] == team_id:
                if gh > ga_:
                    form_points += 3
                elif gh == ga_:
                    form_points += 1
            else:
                if ga_ > gh:
                    form_points += 3
                elif ga_ == gh:
                    form_points += 1

        return {
            "avg_gf": avg_gf,
            "avg_ga": avg_ga,
            "form": form_points / 15,
            "wins": wins,
            "draws": draws,
            "losses": losses
        }

    def rating(self, m):
        attack = m["avg_gf"]
        defense = 1 / (m["avg_ga"] + 0.1)
        form = m["form"] * 3
        return attack * 0.6 + defense * 0.3 + form * 0.1

    def compare(self, a, b):
        ma = self.compute_team_metrics(a)
        mb = self.compute_team_metrics(b)
        ra = self.rating(ma)
        rb = self.rating(mb)

        pa = exp(ra) / (exp(ra) + exp(rb))
        pb = 1 - pa

        score_a = round(ma["avg_gf"] * (0.8 + pa))
        score_b = round(mb["avg_gf"] * (0.8 + pb))

        return {
            "team_a": self.teams[a],
            "team_b": self.teams[b],
            "pa": pa * 100,"pb": pb * 100,
            "sa": score_a,
            "sb": score_b
        }

    def standings(self):
        table = {tid: {"p":0,"w":0,"d":0,"l":0,"gf":0,"ga":0,"pts":0} for tid in self.teams}
        for m in self.matches_raw:
            if m["goals"]["home"] is None:
                continue
            h = m["teams"]["home"]["id"]
            a = m["teams"]["away"]["id"]
            gh = m["goals"]["home"]
            ga = m["goals"]["away"]

            table[h]["p"] += 1
            table[a]["p"] += 1
            table[h]["gf"] += gh
            table[h]["ga"] += ga
            table[a]["gf"] += ga
            table[a]["ga"] += gh

            if gh > ga:
                table[h]["w"] += 1
                table[h]["pts"] += 3
                table[a]["l"] += 1
            elif gh < ga:
                table[a]["w"] += 1
                table[a]["pts"] += 3
                table[h]["l"] += 1
            else:
                table[h]["d"] += 1
                table[a]["d"] += 1
                table[h]["pts"] += 1
                table[a]["pts"] += 1

        rows = []
        for tid, s in table.items():
            rows.append({
                "team": self.teams[tid],
                **s,
                "gd": s["gf"] - s["ga"]
            })
        return sorted(rows, key=lambda x: (x["pts"], x["gd"], x["gf"]), reverse=True)

api = FootballAPI(API_KEY_FOOTBALL)
analyzer = FootballAnalyzer(api)
teams = list(analyzer.teams.keys())
user_state = {}

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Таблица АПЛ", callback_data="standings")],
        [InlineKeyboardButton("Статистика команды", callback_data="team")],
        [InlineKeyboardButton("Сравнить команды", callback_data="compare")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Футбольный анализатор", reply_markup=main_menu_keyboard())

async def show_main_menu(query):
    await query.edit_message_text("Футбольный анализатор", reply_markup=main_menu_keyboard())

async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    cid = q.message.chat_id

    if d == "standings":
        rows = analyzer.standings()
        text = "Таблица АПЛ\n\n"
        for i, r in enumerate(rows, 1):
            text += f"{i}. {r['team']} {r['pts']} очков\n"
        await q.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data="back")]])
        )

    elif d == "team":
        kb = [[InlineKeyboardButton(analyzer.teams[t], callback_data=f"t_{t}")] for t in teams]
        await q.edit_message_text("Выберите команду", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("t_"):
        tid = int(d[2:])
        m = analyzer.compute_team_metrics(tid)
        await q.edit_message_text(
            f"{analyzer.teams[tid]}\n"
            f"Победы: {m['wins']}\n"
            f"Ничьи: {m['draws']}\n"
            f"Поражения: {m['losses']}\n"
            f"Форма: {m['form']:.2f}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data="back")]])
        )

    elif d == "compare":
        user_state[cid] = {}
        kb = [[InlineKeyboardButton(analyzer.teams[t], callback_data=f"a_{t}")] for t in teams]
        await q.edit_message_text("Выберите первую команду", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("a_"):
        user_state[cid]["a"] = int(d[2:])
        kb = [[InlineKeyboardButton(analyzer.teams[t], callback_data=f"b_{t}")]
              for t in teams if t != user_state[cid]["a"]]
        await q.edit_message_text("Выберите вторую команду", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("b_"):
        a = user_state[cid]["a"]
        b = int(d[2:])
        r = analyzer.compare(a, b)
        await q.edit_message_text(
            f"{r['team_a']} против {r['team_b']}\n\n"
            f"Вероятность победы:\n"
            f"{r['team_a']}: {r['pa']:.1f}%\n"
            f"{r['team_b']}: {r['pb']:.1f}%\n\n"
            f"Предполагаемый счет:\n"
            f"{r['sa']} : {r['sb']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data="back")]])
        )
        user_state.pop(cid, None)

    elif d == "back":
        await show_main_menu(q)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handler))
app.run_polling()
