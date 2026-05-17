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
 * - `new_map` / `tier` stay as top-level transport commands
 * - everything else is wrapped in the FW2 action envelope:
 *   `{type:"action", data:{action:type, ...payload}}`
 */
export class WSClient {
  constructor(url = "ws://localhost:8766") {
    this.url = url;
    this._listeners = {};
    this._ws = null;
    this._reconnectDelay = 1500;
    this._connect();
  }

  _connect() {
    this._ws = new WebSocket(this.url);
    this._ws.onopen = () => {
      console.log("[WS] Connected");
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
    this._ws.onclose = () => {
      console.warn(`[WS] Disconnected — retry in ${this._reconnectDelay}ms`);
      this._emit("disconnected", {});
      setTimeout(() => this._connect(), this._reconnectDelay);
    };
    this._ws.onerror = () => this._ws?.close();
  }

  on(event, fn)  { (this._listeners[event] ||= []).push(fn); }
  off(event, fn) {
    if (this._listeners[event])
      this._listeners[event] = this._listeners[event].filter(f => f !== fn);
  }
  send(type, payload = {}) {
    if (this._ws?.readyState !== WebSocket.OPEN) return;
    // Top-level transport commands (not wrapped in action envelope)
    const isTopLevel = type === "new_map" || type === "tier" || type === "tutorial_dismiss" || type === "demo_next";
    const message = isTopLevel
      ? { type, ...payload }
      : { type: "action", data: { action: type, ...payload } };
    this._ws.send(JSON.stringify(message));
  }
  _emit(event, data) {
    (this._listeners[event] || []).forEach(fn => fn(data));
  }
}
