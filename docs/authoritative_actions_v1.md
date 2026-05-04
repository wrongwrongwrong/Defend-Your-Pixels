# authoritative_actions v1

定義 React / tracker / bridge 送往 Python authoritative model 的 action 訊息。

## 目前狀態

- 目前已實作並 authoritative 生效的 action 是 `end_turn`、`move_unit`、`attack_in_direction`。
- Live Old Mick setup flow 另外接受 `choose_side`、`set_hq_candidate`、`confirm_hq`，以及 optional `reset_setup` / `cancel_hq`。
- `upgrade_unit` 已退出目前 integration prototype 範圍；UI 在 backend 模式下停用。
- `move_unit` 目前同時可由 tracker flow 與 React validation layer 送出。

## WebSocket 訊息

```json
{
  "type": "action",
  "data": {
    "action": "end_turn"
  }
}
```

## 已實作 action

### `choose_side`

用途：在 board scan ready 後，決定哪一方先進行 HQ setup。

```json
{
  "action": "choose_side",
  "first_player_side": "old_mick"
}
```

Python 端行為：

- 僅在 `side_selection` phase 接受
- 儲存 `first_player_side`
- 轉入 `hq_placement`

目前 `yu_test1/index.html` 已可在 browser side setup controls 中送出這個 action。

### `set_hq_candidate`

用途：為目前 active setup side 提供 HQ 候選位置。

```json
{
  "action": "set_hq_candidate",
  "side": "p1",
  "position": { "x": 3, "y": 4 }
}
```

Python 端行為：

- 驗證 HQ 是否落在該 side territory 且不在 fence
- 合法時只在 backend/session 暫存 candidate
- public payload 只回傳 `has_candidate` / `confirmed`

目前 live frontend 會在 `hq_placement` phase 接受棋盤點擊並送出這個 action；frontend 只保留 temporary local preview，不 authoritative 保存座標。

### `confirm_hq`

用途：確認當前 side 的 HQ candidate。

```json
{
  "action": "confirm_hq",
  "side": "p1"
}
```

Python 端行為：

- 若該 side 已有 candidate，則鎖定 HQ
- 第一個 HQ confirm 後切換 setup control 給另一方
- 兩個 HQ 都 confirm 後，回傳 `hq_setup_complete` 並進入 `game`
- 確認後 HQ 座標仍保持 hidden，不出現在一般 gameplay payload

目前 `yu_test1/index.html` 已可從 setup controls 送出這個 action。

### `reset_setup`

用途：重置目前 pre-game HQ setup。

```json
{
  "action": "reset_setup"
}
```

目前 `yu_test1/index.html` 在 `hq_placement` phase 提供 restart setup control 送出這個 action。

### `cancel_hq`

用途：與 `reset_setup` 相同，作為 setup reset 的相容 action 名稱。

```json
{
  "action": "cancel_hq"
}
```

### `end_turn`

用途：請 Python model 推進回合，並重新廣播最新 `board_state`。

```json
{
  "action": "end_turn"
}
```

預期結果：

- Python 執行 `GameState.end_turn()`
- `turn`、`active_player`、`move_countdown` 等結果由 Python 更新
- 新 `board_state` 廣播給 React

### `move_unit`

用途：送出 unit 的目標格位，由 Python rules 驗證是否合法並更新 `board_state`。

```json
{
  "action": "move_unit",
  "unit_id": "u0",
  "position": { "x": 4, "y": 3 }
}
```

目前狀態：

- 已由 Python backend 實作
- 可由 tracker flow 產生 move intent
- React validation layer 也可手動送出 move intent

Python 端行為：

- 驗證 `unit_id` 與 `position`
- 呼叫 `GameState.move_unit_to(...)`
- 成功時更新狀態並廣播新 `board_state`
- 失敗時更新 `last_action`

### `attack_in_direction`

用途：讓攻擊單位沿 8 個方向之一做直線攻擊，由 Python rules 判定第一個合法目標以及硬地形擋線。

```json
{
  "action": "attack_in_direction",
  "unit_id": "u0",
  "direction": "up_right"
}
```

Python 端行為：

- 驗證 `unit_id` 與 `direction`
- 呼叫 `GameState.attack_in_direction(...)`
- 沿指定方向搜尋第一個合法敵方目標
- 若先遇到硬地形則攻擊失敗
- 成功時更新 HQ / resource tile 狀態與 `last_action`

## 暫不納入 v1 的 action

### `upgrade_unit`

原因：目前 prototype 優先目標是完成 authoritative 整合主線，不先搬移 upgrade 規則。

目前策略：

- backend 模式下 UI 停用 upgrade
- Python 不提供 upgrade 規則實作

## 下一個建議切入的 action

目前 `move_unit` 與 `attack_in_direction` 已切入。下一個 action 是否需要新增，取決於後續 prototype 是否擴充 upgrade、special attack、或 hidden-information flow。

## 與 tracker 的關係

目前 tracker 會先產生 `move_unit` intent，再交由 Python authoritative model 驗證。

Step 6 下一階段應改成：

- `tracker snapshot`
- 推導為 `move_unit` / 其他 action intent
- Python model 驗證並套用
- 輸出新 `board_state`

也就是 tracker 不應直接覆寫 authoritative model，而應只提供 intent。

## Setup flow 補充

Pre-game setup 與 live tracker flow 現在走 backend-first session state machine：

- `scan`
- `side_selection`
- `hq_placement`
- `game`

During `game`, inactive-side token movement is ignored and surfaced as `inactive_side_token_changed` rather than mutating the authoritative state.
