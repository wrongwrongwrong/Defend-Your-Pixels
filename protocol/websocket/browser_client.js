/**
 * WebSocket client for yu_test2.
 *
 * The server (yu_test2 dev server, or FW2 backend) broadcasts a raw state
 * object — no { event, data } envelope. We translate the latest state into
 * synthetic events:
 *
 *   "connected"     → fired once when the WS opens
 *   "state"         → fired each time a new state arrives  (full payload)
 *   "events"        → fired with the events[] array if non-empty
 *   "disconnected"  → on close
 *
 * Listeners can also `send(type, data)` for client → server messages.
 *
 * Transport rules:
 * - `new_map` / `tier` / `demo_next` stay as top-level transport commands
 * - everything else is wrapped in the FW2 action envelope:
 *   `{type:"action", data:{action:type, ...payload}}`
 *
 * URL: `ws://<hostname>:<port>` where port defaults to 8765 and can be set
 * via `?ws_port=` to match `run_live_tracker --ws-port`.
 */
export function resolveWsUrl(defaultPort = "8765") {
  const params = new URLSearchParams(location.search);
  const port = params.get("ws_port") || defaultPort;
  const host = location.hostname || "localhost";
  return `ws://${host}:${port}`;
}

export class WSClient {
  constructor(url = resolveWsUrl()) {
    this.url = url;
    this._listeners = {};
    this._ws = null;
    this._reconnectDelay = 1500;
    this._reconnectTimer = null;
    this._outbox = [];
    this._connect();
  }

  _connect() {
    if (this._reconnectTimer) {
      clearTimeout(this._reconnectTimer);
      this._reconnectTimer = null;
    }

    this._ws = new WebSocket(this.url);
    this._ws.onopen = () => {
      console.log(`[WS] Connected to ${this.url}`);
      this._flushOutbox();
      this._emit("connected", {});
    };
    this._ws.onmessage = (e) => {
      try {
        const state = JSON.parse(e.data);
        this._emit("state", state);
        if (Array.isArray(state.events) && state.events.length)
          this._emit("events", state.events);
      } catch (err) {
        console.warn("[WS] Bad message:", err);
      }
    };
    this._ws.onclose = (ev) => {
      const detail = `code=${ev.code} reason=${ev.reason || "(none)"} wasClean=${ev.wasClean}`;
      console.warn(`[WS] Disconnected (${detail}) — retry in ${this._reconnectDelay}ms`);
      this._emit("disconnected", { code: ev.code, reason: ev.reason, wasClean: ev.wasClean });
      this._reconnectTimer = setTimeout(() => this._connect(), this._reconnectDelay);
    };
    this._ws.onerror = () => this._ws?.close();
  }

  on(event, fn)  { (this._listeners[event] ||= []).push(fn); }
  off(event, fn) {
    if (this._listeners[event])
      this._listeners[event] = this._listeners[event].filter(f => f !== fn);
  }
  send(type, payload = {}) {
    const isTopLevel = type === "new_map" || type === "tier" || type === "demo_next";
    const message = isTopLevel
      ? { type, ...payload }
      : { type: "action", data: { action: type, ...payload } };
    const json = JSON.stringify(message);
    if (this._ws?.readyState === WebSocket.OPEN) {
      this._ws.send(json);
      return;
    }
    this._outbox.push(json);
    if (this._outbox.length > 32) this._outbox.shift();
  }
  _flushOutbox() {
    if (this._ws?.readyState !== WebSocket.OPEN) return;
    while (this._outbox.length) this._ws.send(this._outbox.shift());
  }
  _emit(event, data) {
    (this._listeners[event] || []).forEach(fn => fn(data));
  }
}
