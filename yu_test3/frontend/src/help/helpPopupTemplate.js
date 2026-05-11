/**
 * Help overlay copy for GameScene (marker IDs, HQ, battle rules).
 * Kept in one module so the path /src/help/helpPopupTemplate.js always resolves
 * (avoids 404 + broken ES module graph when browsers cache older imports).
 */

export const HELP_POPUP_TITLE = "Field Help";

export const HELP_POPUP_LINES = [
  "Show ID5 to keep this help open.",
  "Remove ID5 to return to the normal board view.",
  "",
  "ID10 / ID20  Choose the setup side or start that side's turn.",
  "ID11 / ID21  Place the active side's hidden HQ candidate.",
  "ID4          Confirm HQ placement or submit the active side's attack.",
  "",
  "HQ rules:",
  "- HQ must stay on its own side and never on the fence.",
  "- HQ cannot be on hard terrain or soft terrain.",
  "- Reserved cells are blocked: A1, A2, B1, K12, L11, L12.",
  "",
  "Battle rules:",
  "- Attack tokens must stay on their own side.",
  "- Old Mick attackers fire E / SE / S / SW.",
  "- Mob attackers fire W / NW / N / NE.",
  "- Tier 4 unlocks the nuke button for the active side.",
];

export function getHelpPopupBodyText() {
  return HELP_POPUP_LINES.join("\n");
}

export default getHelpPopupBodyText;
