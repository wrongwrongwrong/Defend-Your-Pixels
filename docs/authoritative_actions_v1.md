# authoritative_actions v1

定義 React / tracker / bridge 送往 Python authoritative model 的 action 訊息。

## 目前狀態

- 目前已實作並 authoritative 生效的 action 是 `end_turn`、`move_unit`、`capture`、`act_on_target`。
- `upgrade_unit` 已退出目前 integration prototype 範圍；UI 在 backend 模式下停用。
- `move_unit` 目前已先接在 tracker-driven flow；React UI 尚未提供手動下達 move 指令的控制。

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

### `end_turn`

用途：請 Python model 推進回合，並重新廣播最新 `board_state`。

```json
{
  "action": "end_turn"
}
```

預期結果：

- Python 執行 `GameState.end_turn()`
- `turn`、`active_player`、`income_per_turn` 相關結果由 Python 更新
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
- 目前主要由 tracker flow 產生 move intent
- React UI 端尚未提供手動 move 控制

Python 端行為：

- 驗證 `unit_id` 與 `position`
- 呼叫 `GameState.move_unit_to(...)`
- 成功時更新狀態並廣播新 `board_state`
- 失敗時更新 `last_action`

### `capture`

用途：讓單位嘗試佔領當前所在格位的 ether drill，由 Python rules 驗證並更新 `board_state`。

```json
{
  "action": "capture",
  "unit_id": "u0"
}
```

Python 端行為：

- 驗證 `unit_id`
- 呼叫 `GameState.capture(...)`
- 成功時更新 drill owner、income 與 `last_action`
- 失敗時更新 `last_action`

### `act_on_target`

用途：讓單位對目標格執行攻擊 / 修復等行為，由 Python rules 驗證並更新 `board_state`。

```json
{
  "action": "act_on_target",
  "unit_id": "u0",
  "target": { "x": 4, "y": 4 }
}
```

Python 端行為：

- 驗證 `unit_id` 與 `target`
- 呼叫 `GameState.act_on_target(...)`
- 成功時更新單位 / 塔 / obstacle 等狀態與 `last_action`
- 失敗時更新 `last_action`

## 暫不納入 v1 的 action

### `upgrade_unit`

原因：目前 prototype 優先目標是完成 authoritative 整合主線，不先搬移 upgrade 規則。

目前策略：

- backend 模式下 UI 停用 upgrade
- Python 不提供 upgrade 規則實作

## 下一個建議切入的 action

目前 `move_unit`、`capture`、`act_on_target` 已切入。下一個可考慮的 action 取決於 prototype 需求，例如：

- `push`

例如 `push` 可考慮：

```json
{
  "action": "push",
  "unit_id": "u0",
  "direction": "right"
}
```

## 與 tracker 的關係

目前 tracker 會先產生 `move_unit` intent，再交由 Python authoritative model 驗證。

Step 6 下一階段應改成：

- `tracker snapshot`
- 推導為 `move_unit` / 其他 action intent
- Python model 驗證並套用
- 輸出新 `board_state`

也就是 tracker 不應直接覆寫 authoritative model，而應只提供 intent。
