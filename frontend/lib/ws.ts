import { WebSocketEnvelope, AnalyticsSnapshot, AlertEvent } from "./contracts";

type EventHandler<T> = (data: T) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectTimeout: any = null;
  private reconnectInterval = 2000;
  private isExplicitlyClosed = false;

  private onSnapshotCallbacks: Set<EventHandler<AnalyticsSnapshot>> = new Set();
  private onAlertCallbacks: Set<EventHandler<AlertEvent>> = new Set();
  private onConnectionCallbacks: Set<(connected: boolean) => void> = new Set();

  constructor() {
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://127.0.0.1:8000/api/v1/ws";
    this.url = wsUrl;
  }

  public connect() {
    if (typeof window === "undefined") return;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.notifyConnection(true);
        if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
      };

      this.ws.onmessage = (event) => {
        try {
          const envelope: WebSocketEnvelope = JSON.parse(event.data);
          this.handleEnvelope(envelope);
        } catch {
          // ignore non-json messages (like 'pong')
        }
      };

      this.ws.onclose = () => {
        this.notifyConnection(false);
        if (!this.isExplicitlyClosed) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = () => {
        this.notifyConnection(false);
      };
    } catch {
      this.scheduleReconnect();
    }
  }

  public disconnect() {
    this.isExplicitlyClosed = true;
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.notifyConnection(false);
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, this.reconnectInterval);
  }

  private notifyConnection(connected: boolean) {
    this.onConnectionCallbacks.forEach((cb) => cb(connected));
  }

  private handleEnvelope(envelope: WebSocketEnvelope) {
    if (envelope.type === "analytics.snapshot.updated") {
      this.onSnapshotCallbacks.forEach((cb) => cb(envelope.data));
    } else if (envelope.type === "alert.created") {
      this.onAlertCallbacks.forEach((cb) => cb(envelope.data));
    }
  }

  public onSnapshot(callback: EventHandler<AnalyticsSnapshot>) {
    this.onSnapshotCallbacks.add(callback);
    return () => {
      this.onSnapshotCallbacks.delete(callback);
    };
  }

  public onAlert(callback: EventHandler<AlertEvent>) {
    this.onAlertCallbacks.add(callback);
    return () => {
      this.onAlertCallbacks.delete(callback);
    };
  }

  public onConnectionChange(callback: (connected: boolean) => void) {
    this.onConnectionCallbacks.add(callback);
    return () => {
      this.onConnectionCallbacks.delete(callback);
    };
  }
}

export const wsClient = new WebSocketClient();
