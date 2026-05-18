/**
 * Browser WebSocket client for the Defend Your Pixels live runtime.
 *
 * The Python runtime broadcasts a raw state object, without a
 * `{ type, data }` envelope. This client translates incoming messages into
 * browser-side events:
 *
 *   "connected"     -> fired once when the WS opens
 *   "state"         -> fired each time a new state arrives (full payload)
 *   "events"        -> fired with the events[] array if non-empty
 *   "disconnected"  -> fired when the socket closes
 *
 * Outbound messages follow the current runtime protocol:
 * - `new_map` / `tier` stay as top-level transport commands.
 * - everything else is wrapped as `{type:"action", data:{action:type, ...payload}}`.
 */
export class WSClient {
  constructor(url = "ws://localhost:8765") {
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
      console.warn(`[WS] Disconnected - retry in ${this._reconnectDelay}ms`);
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
    const message = (type === "new_map" || type === "tier")
      ? { type, ...payload }
      : { type: "action", data: { action: type, ...payload } };
    this._ws.send(JSON.stringify(message));
  }
  _emit(event, data) {
    (this._listeners[event] || []).forEach(fn => fn(data));
  }
}
