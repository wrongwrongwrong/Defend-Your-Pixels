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
 * Listeners can also `send(type, data)` for client → server messages
 * (`{type, ...data}` JSON).
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
    if (this._ws?.readyState === WebSocket.OPEN)
      this._ws.send(JSON.stringify({ type, ...payload }));
  }
  _emit(event, data) {
    (this._listeners[event] || []).forEach(fn => fn(data));
  }
}
