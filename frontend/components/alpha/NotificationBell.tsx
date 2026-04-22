"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type Severity = "info" | "success" | "warning" | "critical";

type NotificationEvent = {
  id: string;
  event_type: string;
  title: string;
  message: string;
  severity: Severity;
  payload: Record<string, unknown>;
  created_at: string;
  read: boolean;
};

const SEVERITY_COLOR: Record<Severity, string> = {
  info: "border-l-terminal-accent/60 bg-terminal-accent/5",
  success: "border-l-green-500/60 bg-green-500/5",
  warning: "border-l-amber-500/60 bg-amber-500/5",
  critical: "border-l-red-500/60 bg-red-500/5",
};

const SEVERITY_DOT: Record<Severity, string> = {
  info: "bg-terminal-accent",
  success: "bg-green-400",
  warning: "bg-amber-400",
  critical: "bg-red-400",
};

function timeAgo(isoString: string): string {
  const delta = Math.floor((Date.now() - new Date(isoString).getTime()) / 1000);
  if (delta < 60) return `${delta}s ago`;
  if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
  if (delta < 86400) return `${Math.floor(delta / 3600)}h ago`;
  return `${Math.floor(delta / 86400)}d ago`;
}

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<NotificationEvent[]>([]);
  const [open, setOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  // Initial fetch of recent notifications
  useEffect(() => {
    fetch(`${API_BASE}/notifications`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.notifications) {
          setNotifications(data.notifications);
        }
      })
      .catch(() => {});
  }, []);

  // SSE stream
  useEffect(() => {
    const es = new EventSource(`${API_BASE}/notifications/stream`, {
      withCredentials: true,
    } as EventSourceInit);
    esRef.current = es;

    es.onmessage = (ev) => {
      try {
        const event: NotificationEvent = JSON.parse(ev.data);
        setNotifications((prev) => {
          const exists = prev.some((n) => n.id === event.id);
          if (exists) return prev;
          return [event, ...prev].slice(0, 100);
        });
      } catch {
        // ignore malformed frames
      }
    };

    es.onerror = () => {
      // EventSource will auto-reconnect; no action needed
    };

    return () => {
      es.close();
    };
  }, []);

  // Close panel on outside click
  useEffect(() => {
    function handleClickOutside(ev: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(ev.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllRead = useCallback(async () => {
    await fetch(`${API_BASE}/notifications/read-all`, {
      method: "POST",
      credentials: "include",
    }).catch(() => {});
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const markOneRead = useCallback(async (id: string) => {
    await fetch(`${API_BASE}/notifications/${id}/read`, {
      method: "POST",
      credentials: "include",
    }).catch(() => {});
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  return (
    <div className="relative" ref={panelRef}>
      {/* Bell button */}
      <button
        onClick={() => {
          setOpen((v) => !v);
          if (!open && unreadCount > 0) markAllRead();
        }}
        className="relative flex h-8 w-8 items-center justify-center rounded border border-terminal-line/30 bg-terminal-panel/60 text-terminal-accent/70 transition hover:border-terminal-accent/50 hover:text-terminal-accent"
        aria-label="Notifications"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white">
            {unreadCount > 99 ? "99" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-10 z-50 w-80 rounded border border-terminal-line/30 bg-terminal-panel shadow-xl">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-terminal-line/20 px-3 py-2">
            <span className="text-xs font-semibold uppercase tracking-widest text-terminal-accent/70">
              Notifications
            </span>
            {notifications.some((n) => !n.read) && (
              <button
                onClick={markAllRead}
                className="text-[10px] text-terminal-accent/50 hover:text-terminal-accent transition"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="px-3 py-6 text-center text-xs text-terminal-accent/40">
                No notifications yet.
              </p>
            ) : (
              notifications.slice(0, 30).map((n) => (
                <button
                  key={n.id}
                  onClick={() => markOneRead(n.id)}
                  className={`w-full border-b border-terminal-line/10 border-l-2 px-3 py-2 text-left transition hover:bg-terminal-line/10 ${
                    SEVERITY_COLOR[n.severity] ?? SEVERITY_COLOR.info
                  } ${n.read ? "opacity-60" : ""}`}
                >
                  <div className="flex items-start gap-2">
                    <span
                      className={`mt-1 h-1.5 w-1.5 shrink-0 rounded-full ${SEVERITY_DOT[n.severity] ?? SEVERITY_DOT.info}`}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[11px] font-medium text-terminal-accent/90">
                        {n.title}
                      </p>
                      <p className="mt-0.5 text-[10px] leading-relaxed text-terminal-accent/60 line-clamp-2">
                        {n.message}
                      </p>
                      <p className="mt-1 text-[9px] text-terminal-accent/35">
                        {timeAgo(n.created_at)}
                      </p>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
