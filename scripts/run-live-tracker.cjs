/**
 * Spawn the live tracker with the repo venv's Python when present (Windows + Unix).
 * Repo root must be the current working directory for `node scripts/run-live-tracker.cjs`.
 */
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const isWin = process.platform === "win32";
const venvPython = isWin
  ? path.join(root, ".venv", "Scripts", "python.exe")
  : path.join(root, ".venv", "bin", "python");

let python = isWin ? "python" : "python3";
if (fs.existsSync(venvPython)) {
  python = venvPython;
} else {
  console.warn(
    "[run-live-tracker] No .venv found; using from PATH:",
    python,
    "(run setup.sh / Windows venv setup first)",
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
