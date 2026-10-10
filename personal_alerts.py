"""Personal, state-based reminders built on Dota 2 Game State Integration.

The timing alerts in flask_server.py only look at the game clock. This module
looks at *your own* hero, items and gold (the only per-player data GSI exposes
while you are playing) and produces short spoken reminders.

PersonalAlerts.update() is pure logic: feed it a GSI payload, get back a list
of messages. Speaker and MatchLogger handle the side effects.
"""

import json
import os
import queue
import threading
import time

IN_PROGRESS = "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS"
CONFIG_FILE = "personal_config.json"


def load_config(path=CONFIG_FILE):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[personal] could not load {path}: {e}")
        return {"enabled": False}


def _item_names(items):
    """All item names the hero currently owns (inventory, backpack, stash)."""
    names = set()
    for slot, item in (items or {}).items():
        if isinstance(item, dict):
            name = item.get("name")
            if name and name != "empty":
                names.add(name)
    return names


class PersonalAlerts:
    def __init__(self, config=None):
        self.config = config if config is not None else load_config()
        self.reset()

    def reset(self):
        self.match_id = None
        self.last_said = {}          # rule key -> game clock when last said
        self.ult_was_on_cd = False
        self.done_once = set()       # one-shot keys (last-hit checkpoints, item goals)

    # -- helpers ---------------------------------------------------------
    def _rule(self, name):
        rule = self.config.get(name, {})
        return rule if rule.get("enabled") else None

    def _throttled(self, key, clock, repeat):
        last = self.last_said.get(key)
        if last is not None and clock - last < repeat:
            return True
        self.last_said[key] = clock
        return False

    # -- main entry ------------------------------------------------------
    def update(self, data):
        if not self.config.get("enabled"):
            return []

        game = data.get("map") or {}
        if game.get("game_state") != IN_PROGRESS:
            return []

        match_id = game.get("matchid")
        if match_id != self.match_id:
            self.reset()
            self.match_id = match_id

        clock = game.get("clock_time", 0)
        minute = clock // 60
        hero = data.get("hero") or {}
        player = data.get("player") or {}
        items = data.get("items") or {}
        abilities = data.get("abilities") or {}
        alive = hero.get("alive", True)
        gold = player.get("gold", 0)
        owned = _item_names(items)

        out = []

        # No TP scroll in the TP slot
        rule = self._rule("no_tp")
        if rule and alive and minute >= rule["after_minute"]:
            tp = (items.get("teleport0") or {}).get("name", "empty")
            if tp == "empty" and not self._throttled("no_tp", clock, rule["repeat_seconds"]):
                out.append(rule["message"])

        # Low HP
        rule = self._rule("low_hp")
        if rule and alive and 0 < hero.get("health_percent", 100) < rule["percent"]:
            if not self._throttled("low_hp", clock, rule["repeat_seconds"]):
                out.append(rule["message"])

        # Ultimate came off cooldown
        rule = self._rule("ultimate_ready")
        if rule:
            ult = next((a for a in abilities.values()
                        if isinstance(a, dict) and a.get("ultimate")), None)
            if ult and ult.get("level", 0) > 0:
                on_cd = ult.get("cooldown", 0) > 0
                if self.ult_was_on_cd and not on_cd and ult.get("can_cast", True):
                    out.append(rule["message"])
                self.ult_was_on_cd = on_cd

        # Not enough gold to buy back
        rule = self._rule("buyback")
        if rule and alive and minute >= rule["after_minute"]:
            cost = hero.get("buyback_cost", 0)
            if cost and gold < cost and not self._throttled("buyback", clock, rule["repeat_seconds"]):
                out.append(rule["message"])

        # Sitting on too much gold
        rule = self._rule("unspent_gold")
        if rule and alive and gold >= rule["threshold"]:
            if not self._throttled("unspent_gold", clock, rule["repeat_seconds"]):
                out.append(rule["message"])

        # Last-hit checkpoints
        rule = self._rule("last_hit_targets")
        if rule:
            for m, target in rule["targets"].items():
                key = f"lh_{m}"
                if minute >= int(m) and key not in self.done_once:
                    self.done_once.add(key)
                    actual = player.get("last_hits", 0)
                    if minute == int(m) and actual < target:
                        out.append(rule["message"].format(minute=m, actual=actual, target=target))

        # Enough gold for a goal item you don't own yet
        rule = self._rule("item_goals")
        if rule:
            for goal in rule["items"]:
                key = f"item_{goal['name']}"
                if goal["name"] in owned:
                    self.done_once.add(key)
                elif key not in self.done_once and gold >= goal["cost"]:
                    self.done_once.add(key)
                    out.append(rule["message"].format(label=goal["label"]))

        return out


class Speaker:
    """Text-to-speech on a single background thread (pyttsx3 is not thread-safe)."""

    def __init__(self, rate=190):
        self.q = queue.Queue()
        self.rate = rate
        threading.Thread(target=self._run, daemon=True).start()

    def say(self, text):
        print(f"[personal] {text}")
        self.q.put(text)

    def _run(self):
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", self.rate)
            for voice in engine.getProperty("voices"):
                langs = " ".join(str(l) for l in (voice.languages or []))
                if "zh" in langs.lower() or "chinese" in voice.name.lower() \
                        or "huihui" in voice.name.lower():
                    engine.setProperty("voice", voice.id)
                    break
        except Exception as e:
            print(f"[personal] TTS unavailable, printing only: {e}")
            engine = None
        while True:
            text = self.q.get()
            if engine:
                engine.say(text)
                engine.runAndWait()


class MatchLogger:
    """Writes a compact snapshot every few game-seconds to match_logs/<matchid>.jsonl."""

    def __init__(self, config):
        self.enabled = config.get("enabled", False)
        self.folder = config.get("folder", "match_logs")
        self.every = config.get("every_seconds", 5)
        self.last_clock = None

    def log(self, data):
        if not self.enabled:
            return
        game = data.get("map") or {}
        if game.get("game_state") != IN_PROGRESS:
            return
        clock = game.get("clock_time", 0)
        if self.last_clock is not None and 0 <= clock - self.last_clock < self.every:
            return
        self.last_clock = clock

        hero = data.get("hero") or {}
        player = data.get("player") or {}
        row = {
            "t": clock,
            "wall": time.time(),
            "hero": hero.get("name"),
            "level": hero.get("level"),
            "alive": hero.get("alive"),
            "hp_pct": hero.get("health_percent"),
            "gold": player.get("gold"),
            "nw": player.get("net_worth"),
            "lh": player.get("last_hits"),
            "dn": player.get("denies"),
            "k": player.get("kills"),
            "d": player.get("deaths"),
            "a": player.get("assists"),
            "gpm": player.get("gpm"),
            "xpm": player.get("xpm"),
            "items": sorted(_item_names(data.get("items"))),
        }
        os.makedirs(self.folder, exist_ok=True)
        path = os.path.join(self.folder, f"{game.get('matchid', 'unknown')}.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
