"""Run with: python -m pytest test_personal_alerts.py  (or just python test_personal_alerts.py)"""

import copy
import json

from personal_alerts import PersonalAlerts, load_config

BASE = {
    "map": {"matchid": "1", "game_state": "DOTA_GAMERULES_STATE_GAME_IN_PROGRESS", "clock_time": 300},
    "player": {"gold": 500, "last_hits": 40},
    "hero": {"alive": True, "health_percent": 90, "buyback_cost": 1000},
    "items": {"slot0": {"name": "item_power_treads"}, "teleport0": {"name": "item_tpscroll"}},
    "abilities": {"ability3": {"name": "x_ult", "level": 1, "ultimate": True, "cooldown": 0, "can_cast": True}},
}


def state(**changes):
    d = copy.deepcopy(BASE)
    for path, value in changes.items():
        section, key = path.split("__")
        d[section][key] = value
    return d


def make():
    return PersonalAlerts(load_config())


def test_quiet_when_nothing_wrong():
    assert make().update(state()) == []


def test_ignored_outside_game():
    assert make().update(state(map__game_state="DOTA_GAMERULES_STATE_PRE_GAME", hero__health_percent=5)) == []


def test_no_tp_throttled():
    a = make()
    d = state()
    d["items"]["teleport0"] = {"name": "empty"}
    assert "背包没有TP" in a.update(d)
    d["map"]["clock_time"] = 330
    assert "背包没有TP" not in a.update(d)
    d["map"]["clock_time"] = 361
    assert "背包没有TP" in a.update(d)


def test_low_hp():
    assert "血量低" in make().update(state(hero__health_percent=10))


def test_ultimate_ready_on_transition_only():
    a = make()
    d = state()
    d["abilities"]["ability3"]["cooldown"] = 40
    assert a.update(d) == []
    d["abilities"]["ability3"]["cooldown"] = 0
    d["map"]["clock_time"] = 340
    assert "大招好了" in a.update(d)
    d["map"]["clock_time"] = 341
    assert "大招好了" not in a.update(d)


def test_last_hit_checkpoint():
    out = make().update(state(map__clock_time=600, player__last_hits=50))
    assert any("补刀50" in m for m in out)


def test_item_goal_once_and_skipped_if_owned():
    a = make()
    out = a.update(state(player__gold=2300))
    assert "钱够买跳刀了" in out
    assert "钱够买跳刀了" not in a.update(state(player__gold=2400, map__clock_time=310))
    b = make()
    d = state(player__gold=2300)
    d["items"]["slot1"] = {"name": "item_blink"}
    assert "钱够买跳刀了" not in b.update(d)


def test_buyback_and_unspent_gold():
    out = make().update(state(map__clock_time=1600, player__gold=3000, hero__buyback_cost=3500))
    assert "买活钱不够" in out and "钱太多了，回家花钱" in out


def test_new_match_resets_state():
    a = make()
    a.update(state(player__gold=2300))
    out = a.update(state(player__gold=2300, map__matchid="2"))
    assert "钱够买跳刀了" in out


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
