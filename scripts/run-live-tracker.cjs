/**
 * Spawn the live tracker with the repo venv's Python when present (Windows + Unix).
 * Repo root must be the current working directory for `node scripts/run-live-tracker.cjs`.
 */
const { spawn } = require("child_process");
const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const isWin = process.platform === "win32";
const activeVenvPython = process.env.VIRTUAL_ENV
  ? path.join(
      process.env.VIRTUAL_ENV,
      isWin ? path.join("Scripts", "python.exe") : path.join("bin", "python"),
    )
  : null;
const configuredPython = process.env.DEFEND_YOUR_PIXELS_PYTHON || null;
const candidatePythons = [
  configuredPython,
  activeVenvPython,
  isWin ? path.join(root, ".venv", "Scripts", "python.exe") : path.join(root, ".venv", "bin", "python"),
  isWin ? path.join(root, "dyp", "Scripts", "python.exe") : path.join(root, "dyp", "bin", "python"),
].filter(Boolean);

function isUsablePython(candidate) {
  if (!candidate || !fs.existsSync(candidate)) {
    return false;
  }

  const result = spawnSync(candidate, ["--version"], { stdio: "ignore" });
  return result.status === 0;
}

let python = isWin ? "python" : "python3";
const existingPython = candidatePythons.find((candidate) => isUsablePython(candidate));
if (existingPython) {
  python = existingPython;
} else {
  console.warn(
    "[run-live-tracker] No repo virtualenv found; using from PATH:",
    python,
    `(tried: ${candidatePythons.join(", ") || "none"})`,
  );
}

const child = spawn(python, ["-m", "runner.run_live_tracker"], {
  cwd: root,
  stdio: "inherit",
});

child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code ?? 1);
});
