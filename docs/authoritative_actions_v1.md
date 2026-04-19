# authoritative_actions v1

定義 React / tracker / bridge 送往 Python authoritative model 的 action 訊息。

## 目前狀態

- 目前已實作並 authoritative 生效的 action 是 `end_turn`、`move_unit`、`attack_in_direction`。
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
