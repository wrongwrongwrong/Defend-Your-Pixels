# board_state v1（最小 contract）

Note: the broader Old Mick frontend/backend contract is now documented in
`docs/frontend_backend_contract_v1.md`. This file remains the narrower board-state payload reference.

供 Python（權威）、bridge（傳輸）、React（顯示）共用語意。第一版刻意**不**包含：`phase`、完整規則樹、動畫專用欄位、tracker 校準細節（校準可續用現有 `tracker_frame`）。

## WebSocket 訊息

| `type` | 語意 |
|--------|------|
| `board_state` | 權威遊戲快照；React **整份替換** UI state（經 `adaptBoardStateToUi`）。 |
| `action` | React / tracker 送往 Python 的 authoritative action。見 [`authoritative_actions_v1.md`](authoritative_actions_v1.md)。 |
| `tracker_frame` | 僅 marker → 合併 **位置 / 朝向**（現有 `applyTrackedTokens`）。 |
| `game_state` | **Legacy**：與 `tracker_frame` 相同合併語意，保留舊 bridge 相容。 |

## Authoritative JSON（Python / bridge 輸出建議形狀）

欄位命名採 **snake_case**，與 `model_backend` 對齊；React 端 adapter 負責轉成現有 camelCase UI shape（見下節）。v1 authoritative payload 固定以 `units[]` 表示棋盤單位，不直接輸出 React 專用的 `players[].tokens[]` 形狀。

```json
{
  "turn": 1,
  "active_player": 1,
  "game_over": false,
  "winner": null,
  "last_action": "Ready",
  "players": [
    {
      "id": 1,
      "ether": 0,
      "income_per_turn": 0,
      "hq_name": "Homestead",
      "resource_name": "Wheat Paddock",
      "command_tower_position": { "x": 5, "y": 11 },
      "command_tower_hp": 20,
      "command_tower_max_hp": 20
    }
  ],
  "resource_tiles": [
    {
      "id": "px0",
      "owner": 1,
      "theme_name": "Wheat Paddock",
      "position": { "x": 4, "y": 10 },
      "protection_layers": 1
    }
  ],
  "units": [
    {
      "id": "A1",
      "owner": 1,
      "kind": "attacker",
      "position": { "x": 3, "y": 10 },
      "rotation_deg": 0,
      "hp": 3,
      "max_hp": 3
    }
  ]
}
```

- `winner`：`null` 或 `1` / `2`（與 `PlayerId` 一致）。
- `last_action`：optional；有值時供 HUD / debug 顯示，沒有時前端可忽略。
- `units[].id`：固定使用 `string`，與 `model_backend` 既有 unit id（如 `A1`、`D2`）一致。
- `units[].rotation_deg`：optional；若無，adapter 預設轉成 UI `rotation: "forward"`，或由 tracker 補。
- `resource_tiles[]`：authoritative destructible objectives，提供 owner、position、theme name 與 protection layer。
- **塔**：v1 固定摺進 `players[]` 的 `command_tower_position` / `command_tower_hp` / `command_tower_max_hp`；不另開 `towers` 陣列。
- `players[].hq_name` / `players[].resource_name`：提供 `Old Mick` 主題名稱給 React / Phaser 顯示。
- `players[].income_per_turn`：目前在 Old Mick MVP 中屬 placeholder 欄位，保留給後續 economy/resource work。

## UI consume 形狀（React 現狀）

與 [`createInitialGameState`](../react_frontend/src/game/turns.js) 對齊，精簡列出：

| UI 欄位 | 說明 |
|---------|------|
| `turn` | number |
| `activePlayer` | `1` \| `2` |
| `gameOver` | boolean |
| `players[]` | `id`, `color`, `zone`, `ether`, `incomePerTurn`, `hqName`, `resourceName`, `commandTowerPosition`, `commandTowerHp`, `commandTowerMaxHp`, `tokens[]` |
| `resourceTiles[]` | `id`, `owner`, `themeName`, `position`, `protectionLayers` |
| `players[].tokens[]` | `id`, `kind`, `hp`, `maxHp`, `position`, `rotation`（字串 facing 或相容格式） |
| `units[]` | 棋盤上非 marker 單位（目前多為 `[]`） |

- `color`、`zone` 為 UI-only 欄位，由 React adapter 依 `player.id` 補上；不由 Python authoritative payload 提供。

## Adapter：`units` → `players[].tokens[]`（概念）

| Authoritative | UI token 欄位 |
|---------------|----------------|
| `units[].id`（string） | `id`：UI 端沿用 string，不做 `Number(id)` 轉換 |
| `units[].owner` | 決定 token 掛在哪個 `player` |
| `units[].kind` | `kind`：`attacker` \| `defender` |
| `units[].position` | `position`：`{ x, y }`（格座標） |
| `units[].rotation_deg` | `rotation`：經 `degreesToFacing` 或對照表 → `forward` / `right` / … |
| `units[].hp` / `max_hp` | `hp` / `maxHp` |

定案：authoritative payload 維持 `units[]`；`react_frontend/src/bridge/adaptBoardStateToUi.js` 負責組裝 `players[].tokens[]`，保留現有 React UI consume 形狀。

## HP 尺度策略

| 來源 | 範例 |
|------|------|
| `model_backend` `Unit` | 預設 `hp` / `max_hp` 為小整數（如 3）。 |
| 現有 React token | 如 30 / 40（展示用條較細緻）。 |

**建議（擇一，團隊定案）：**

1. **單一權威整數**：Python 與 contract 只用一套數字；React 僅顯示比例 `hp / max_hp`（推薦，簡單一致）。
2. **Contract 加 `display_scale`**：後端傳倍率，前端乘上再畫條（兩套數字並存，易混亂）。
3. **僅在 adapter 乘常數**：過渡期把 3 → 30 顯示；需在文件中寫死倍率並與機制稿同步。

第一版 MVP 定案採 **(1)**，條形圖用比例即可，無需與舊 30/40 一致。

## 與目前整合狀態的對應

- 舊的前端 `endTurn` / `trySpendEther` / `phaseForTurn` mock 規則已退出 React validation 主線。
- 目前 authoritative action 已有 `end_turn`、`move_unit`、`attack_in_direction`；見 [`authoritative_actions_v1.md`](authoritative_actions_v1.md)。
- Tracker：仍走 `tracker_frame`，不與 `board_state` 混成同一條「全量又只改位置」的路徑。

## Step 2 定案摘要

- `phase` 不進 v1 authoritative contract。
- `units[].id` 固定為 `string`。
- authoritative payload 固定輸出 `units[]`；React adapter 轉成 `players[].tokens[]`。
- `players[]` 不放 `color` / `zone`；由前端補 UI-only 欄位。
- 塔資料固定摺進 `players[]`。
