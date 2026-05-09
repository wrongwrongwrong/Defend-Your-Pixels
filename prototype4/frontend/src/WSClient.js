/**
 * WebSocket client — emits events via a simple listener map.
 * Usage: ws.on("board_state", handler)
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
        const { event, data } = JSON.parse(e.data);
        this._emit(event, data);
      } catch {}
    };
    this._ws.onclose = () => {
      console.warn("[WS] Disconnected — retrying in", this._reconnectDelay, "ms");
      this._emit("disconnected", {});
      setTimeout(() => this._connect(), this._reconnectDelay);
    };
    this._ws.onerror = () => this._ws.close();
  }

  on(event, fn) {
    (this._listeners[event] ||= []).push(fn);
  }

  off(event, fn) {
    if (this._listeners[event])
      this._listeners[event] = this._listeners[event].filter(f => f !== fn);
  }

  send(event, data = {}) {
    if (this._ws?.readyState === WebSocket.OPEN)
      this._ws.send(JSON.stringify({ event, data }));
  }

  _emit(event, data) {
    (this._listeners[event] || []).forEach(fn => fn(data));
  }
}
