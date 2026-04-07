# Integration Checkpoint 2026-04-05

## 目前結論

- React UI prototype 已保留，主版 `react_frontend/` 目前可被 Python `board_state` 驅動。
- Python 已是 authoritative state source。
- 目前已打通 `React/tracker -> action or intent -> Python model -> board_state -> React` 主線。
- Step 5 主幹已可用；Step 6 已開始建立在 action-based 架構上。

## 已完成項目

### State contract

- `docs/board_state_v1.md` 已定稿。
- authoritative payload 使用 `snake_case`。
- Python 輸出 `units[]`，React adapter 轉成 `players[].tokens[]`。

### Authoritative actions

見 `docs/authoritative_actions_v1.md`。

目前已實作：

- `end_turn`
- `move_unit`
- `capture`
- `act_on_target`

目前不做：

- `upgrade_unit`

### Tracker integration

- tracker snapshot 仍會輸出 `tracker_frame`。
- tracker 不再直接覆寫 Python authoritative model。
- tracker 現在先產生 `move_unit` intents，再交給 Python rules 驗證。
- `rotation_deg` 仍可隨 `board_state.units[]` 一起送到 React。

### Frontend behavior

- backend 連線時，React 不再本地計算 authoritative state。
- `End turn` 會送到 Python。
- upgrade UI 在 backend 模式下停用。
- 畫面可顯示 backend `last_action` / status。

## 本次檢查結果

### 1. move_unit -> board_state

已驗證：

- Python action `move_unit` 成功後，unit 位置會更新。
- `last_action` 會反映移動結果。

驗證結果摘要：

- 初始：`turn=1`, `active_player=1`
- `move_unit(u0 -> (5,1))` 後：`last_action = "u0 moved to (5, 1)"`

### 2. end_turn -> board_state

已驗證：

- `end_turn` 會由 Python 更新回合與 active player。

驗證結果摘要：

- `turn: 1 -> 2`
- `active_player: 1 -> 2`
- `last_action = "Player 2 turn started"`

### 3. capture -> board_state

已驗證：

- `capture` 成功後，drill owner 與 `income_per_turn` 會更新。

驗證結果摘要：

- `last_action = "u0 captured drill at (1, 1)"`
- `income_per_turn = 5`

### 4. Frontend verification

已驗證：

- `npm run build` 通过
- `npm run lint` 通过

## 目前缺口

- React UI 端尚未提供手動 `move_unit` / `capture` 控制。
- React UI 端尚未提供手動 `act_on_target` 控制。
- tracker 與 unit 的 mapping 目前仍是 prototype 級做法，不是最終版。
- tracker flow 仍偏向單位位置驅動，尚未完整推導更高層 action。

## 建議下一步

1. 視 prototype 需求，決定是否補 React 手動 `act_on_target` 控制。
2. 視 prototype 需求，決定 React 是否要加入手動 move / capture 控制。
3. 若要繼續 Step 6，再把 tracker intent 從單純 `move_unit` 擴展到更完整的 action 推導。
