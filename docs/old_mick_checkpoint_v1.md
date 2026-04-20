# Old Mick Checkpoint v1

This document defines the Step 10 checkpoint for the current `Old Mick Against the Mob`
MVP.

It exists to answer a different question from the smoke tests:

- smoke tests ask whether the rules work correctly
- checkpoint testing asks whether the current core loop is worth keeping

## Goal

Use the current playable prototype to validate three decisions:

1. Is directional line attack fun and understandable?
2. Does defender protection create meaningful positioning choices?
3. Do resource tiles stop the game from becoming only an HQ rush?

## What is already complete

The following technical checks are already covered elsewhere:

- line attack hits first valid target
- hard terrain blocks attacks
- protected resource tiles take two hits
- HQ destruction ends the game immediately

See:

- `docs/old_mick_core_test_cases.md`
- `runner/run_old_mick_core_smoke.py`

## What this checkpoint still needs

This checkpoint is about internal gameplay evaluation, not low-level correctness.

The team should now run short internal matches and answer the questions below.

## Recommended setup

Use one of these:

- React validation layer + Python backend

The checkpoint does not require Phaser.

## Minimum session format

Run at least 3 short internal test matches.

Recommended structure:

### Match 1

- play normally
- no explanation after the first rules briefing
- observe confusion points only

### Match 2

- play with attention on defender positioning
- deliberately test whether players protect resource tiles or ignore them

### Match 3

- play with attention on win path
- observe whether both sides still only rush HQ

## Questions to answer

### A. Directional attack

- Do players understand they are choosing a direction, not a target tile?
- Do players understand why the first object on the line is hit?
- Do blocked attacks feel fair?
- Do players need repeated explanation to use the attack system?

### B. Defender protection

- Do players notice that defenders protect nearby resource tiles?
- Does defender placement influence decisions?
- Do players intentionally move around the protection zone?
- Does passive protection feel meaningful or too invisible?

### C. Resource tiles versus HQ rush

- Do players attack resource tiles at all?
- Do resource tiles create alternate priorities?
- Does the game still collapse into direct HQ rushing every time?
- If yes, is that because the rule is weak, or because the UI does not surface tile importance clearly enough?

## What to record

For each internal match, record:

- who played
- prototype used (`React` or `Pygame`)
- approximate match length
- confusion points
- whether resource tiles were targeted
- whether defender zones affected decisions
- whether the match ended by HQ destruction

## Suggested result template

```md
### Match X
- Prototype: React / Pygame
- Length: ~N minutes
- Players understood directional attack: Yes / No
- Defender zone affected decisions: Yes / No
- Resource tiles were targeted: Yes / No
- Ended as HQ rush: Yes / No
- Main issue observed:
- Suggested change:
```

## Decision outcomes

After the checkpoint, choose one of these outcomes:

### Outcome A: core loop is working

Keep moving forward to:

- Step 11 upgrades
- Week 8 prototype testing prep

### Outcome B: rules are technically correct, but the loop is unclear

Prioritize:

- stronger attack-line feedback
- stronger defender-zone visibility
- clearer resource tile emphasis in frontend

### Outcome C: game still collapses into HQ rush

Revisit one or more of:

- resource tile density
- resource tile placement
- defender value
- whether attrition should be introduced earlier

## Current status

At the time of writing:

- technical rule verification is complete
- integration between backend and React validation is in place
- resource tiles are now first-class payload data
- the remaining checkpoint work is the internal gameplay evaluation itself

## Related docs

- `docs/old_mick_mvp_rules.md`
- `docs/old_mick_core_test_cases.md`
- `docs/interaction_flow_v1.md`
- `docs/frontend_backend_contract_v1.md`
