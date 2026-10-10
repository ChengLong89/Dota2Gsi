# Dota 2 Timer and Roshan Overlay

This project provides a simple Dota 2 timer and Roshan overlay for your desktop, offering a convenient way to keep track of in-game time and events. The overlay includes a countdown timer for Roshan's respawn, and the timer plays audio alerts for different in-game events such as stacking, lotus and exp rune.

## Features

- In-game timer that tracks the current Dota 2 game time
- Roshan respawn countdown overlay with color-coding: red for the first 1/3, yellow for the second 1/3, and green for the last 3 minutes.
- Plays an audio alert when Roshan respawns
- Provides audible alerts for stacking camps, express runes, and a third customizable sound alert.
- Hotkey support: Press 'F21' to start/reset the Roshan timer, 'Page Down' to stop the script (an audio alert plays on termination), 'F22' to send the current Roshan time to chat, and 'Page Up' to mute the sounds.

## Setup and Installation

This project requires Python 3.8 or higher. Follow the steps below to set it up:

1. Clone the repository: `git clone https://github.com/Kiyogitpy/Dota2Gsi`
2. Navigate to the project directory: `cd your-directory/Dota2Gsi`
3. Install the required Python packages: `pip install -r requirements.txt`
4. Run the script: `python main.py`

Or alternativly use the release and just run the main.exe

To configure the Dota client to report gamestate, you need to add a config file in steamapps\common\dota 2 beta\game\dota\cfg\gamestate_integration\. The file must use the name pattern called gamestate_integration_*.cfg, for example gamestate_integration_dota2-gsi.cfg.

The gamestate_integration_dota2-gsi.cfg is included in this repository, you can copy it straight into your Dota directory to get started.

## Usage

- After launching the script, "home" is the keybind to make the ui visible or hide it, by default f21 is the key for roshan timer.
- The timer will count down, changing colors as it progresses.
- When the countdown reaches zero, an audio alert will play, and the overlay will disappear.
- Press 'Page Down' to stop the script. An audio alert will play upon termination.
- Press 'F22' to send the current Roshan time to chat.
- Press 'M' to mute all sounds.

## License

This project is licensed under the terms of the MIT license.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


## 个性化提醒（personal-alerts 分支）

在原有计时提醒之外，`personal_alerts.py` 根据 GSI 里你自己的英雄、物品和金钱做语音提醒：

| 提醒 | 触发条件 |
|---|---|
| 背包没有TP | 3 分钟后 TP 栏为空（60 秒内不重复） |
| 血量低 | 血量低于 25% |
| 大招好了 | 大招从冷却变为可用 |
| 买活钱不够 | 25 分钟后金钱低于买活费用 |
| 钱太多了 | 活着且手上金钱超过 2500 |
| 补刀落后 | 5/10/15/20 分钟补刀低于目标 |
| 钱够买 X | 金钱够买目标装备且还没买（每局一次） |

所有阈值、文案和目标装备都在 `personal_config.json` 里改（单独存放，避免被菜单保存时覆盖）。装备价格随版本变化，请按当前补丁核对。静音键对这些提醒同样生效。

每局还会把快照写到 `match_logs/<matchid>.jsonl`，赛后运行：

```
python analyze_match.py            # 最近一局：补刀节点、出装时间、死亡时间、囤钱时长
python analyze_match.py --plot     # 另存经济 / 补刀曲线图（需要 matplotlib）
```

安装：`pip install -r requirements.txt`（新增 pyttsx3，用 Windows 自带语音；装了中文语音包会自动选中文）。
测试：`python test_personal_alerts.py`
