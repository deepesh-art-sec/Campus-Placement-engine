import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Badge } from "../../components/common/Badge";
import { AlertBanner } from "../../components/common/AlertBanner";
import {
  Bell,
  AlertTriangle,
  Clock,
  CheckCircle2,
  Calendar,
  MessageSquare,
  ShieldAlert,
  Check,
  RefreshCw,
  Search,
  Filter,
  ArrowRight,
  Inbox,
} from "lucide-react";

interface NotificationItem {
  id: string;
  category: "needs_review" | "clash_alert" | "request_update" | "schedule_change" | "result_pending" | string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
  metadata: Record<string, any>;
}

interface CoordinatorNotificationsViewProps {
  onNavigateTab?: (tabId: string) => void;
}

export const CoordinatorNotificationsView: React.FC<CoordinatorNotificationsViewProps> = ({
  onNavigateTab,
}) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get<NotificationItem[]>("/api/coordinator/notifications");
      setNotifications(res || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load notifications.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNotifications();
  }, []);

  const handleMarkAsRead = async (id: string) => {
    try {
      await api.post(`/api/coordinator/notifications/${id}/read`, {});
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch (err: any) {
      console.error("Failed to mark notification read", err);
    }
  };

  const handleMarkAllRead = async () => {
    const unread = notifications.filter((n) => !n.is_read);
    for (const item of unread) {
      try {
        await api.post(`/api/coordinator/notifications/${item.id}/read`, {});
      } catch (e) {
        // Continue marking remaining
      }
    }
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  };

  const filteredNotifications = notifications.filter((n) => {
    if (showUnreadOnly && n.is_read) return false;
    if (activeCategory === "all") return true;
    if (activeCategory === "announcement") return n.category === "announcement" || n.category === "broadcast";
    return n.category === activeCategory;
  });

  const getCategoryBadge = (cat: string) => {
    switch (cat) {
      case "announcement":
      case "broadcast":
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-cyan-700 bg-cyan-50 px-2 py-0.5 rounded border border-cyan-200">
            <Bell className="w-3 h-3 text-cyan-600" /> Announcement
          </span>
        );
      case "urgent_alert":
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
            <AlertTriangle className="w-3 h-3 text-rose-600" /> Urgent Broadcast
          </span>
        );
      case "clash_alert":
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
            <AlertTriangle className="w-3 h-3 text-rose-600" /> Clash Alert
          </span>
        );
      case "needs_review":
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
            <ShieldAlert className="w-3 h-3 text-amber-600" /> Needs Review
          </span>
        );
      case "request_update":
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
            <MessageSquare className="w-3 h-3 text-indigo-600" /> Officer Reply
          </span>
        );
      case "schedule_change":
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
            <Calendar className="w-3 h-3 text-purple-600" /> Schedule Update
          </span>
        );
      case "result_pending":
        return (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Result Entry
          </span>
        );
      default:
        return (
          <span className="text-[11px] font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
            {cat.replace(/_/g, " ")}
          </span>
        );
    }
  };

  const getTargetTabForNotification = (cat: string): string | null => {
    switch (cat) {
      case "announcement":
      case "broadcast":
        return "drives";
      case "urgent_alert":
        return "communication";
      case "clash_alert":
        return "clashes";
      case "needs_review":
        return "eligibility";
      case "request_update":
        return "requests";
      case "schedule_change":
        return "schedule";
      case "result_pending":
        return "results";
      default:
        return null;
    }
  };

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900">Notifications & Alerts</h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
              Module 12
            </span>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Real-time operational alerts: needs-review records, schedule clashes, Officer responses, and timetable changes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchNotifications}
            className="p-2 border border-slate-300 rounded-lg hover:bg-slate-50 text-slate-600 transition"
            title="Refresh notifications"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-indigo-600" : ""}`} />
          </button>
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="flex items-center gap-1.5 px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 transition"
            >
              <Check className="w-3.5 h-3.5 text-emerald-600" />
              Mark all as read
            </button>
          )}
        </div>
      </div>

      {error && <AlertBanner type="danger" message={error} onClose={() => setError(null)} />}

      {/* Category Filter Pills & Unread Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-sm">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setActiveCategory("all")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeCategory === "all"
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            All Alerts ({notifications.length})
          </button>
          <button
            onClick={() => setActiveCategory("announcement")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeCategory === "announcement"
                ? "bg-cyan-600 text-white shadow-2xs"
                : "bg-cyan-50 text-cyan-700 hover:bg-cyan-100"
            }`}
          >
            Announcements ({notifications.filter((n) => n.category === "announcement" || n.category === "broadcast").length})
          </button>
          <button
            onClick={() => setActiveCategory("needs_review")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeCategory === "needs_review"
                ? "bg-amber-600 text-white"
                : "bg-amber-50 text-amber-700 hover:bg-amber-100"
            }`}
          >
            Needs Review ({notifications.filter((n) => n.category === "needs_review").length})
          </button>
          <button
            onClick={() => setActiveCategory("clash_alert")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeCategory === "clash_alert"
                ? "bg-rose-600 text-white"
                : "bg-rose-50 text-rose-700 hover:bg-rose-100"
            }`}
          >
            Clash Alerts ({notifications.filter((n) => n.category === "clash_alert").length})
          </button>
          <button
            onClick={() => setActiveCategory("request_update")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeCategory === "request_update"
                ? "bg-indigo-600 text-white"
                : "bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
            }`}
          >
            Officer Replies ({notifications.filter((n) => n.category === "request_update").length})
          </button>
          <button
            onClick={() => setActiveCategory("schedule_change")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeCategory === "schedule_change"
                ? "bg-purple-600 text-white"
                : "bg-purple-50 text-purple-700 hover:bg-purple-100"
            }`}
          >
            Schedule Changes ({notifications.filter((n) => n.category === "schedule_change").length})
          </button>
        </div>

        <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-600 px-2 py-1">
          <input
            type="checkbox"
            checked={showUnreadOnly}
            onChange={(e) => setShowUnreadOnly(e.target.checked)}
            className="rounded text-indigo-600 focus:ring-indigo-500"
          />
          Show unread only ({unreadCount})
        </label>
      </div>

      {/* Notifications List */}
      <div className="space-y-3">
        {loading && notifications.length === 0 ? (
          <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-600 mb-2" />
            Loading operational notifications...
          </div>
        ) : filteredNotifications.length === 0 ? (
          <div className="p-12 text-center text-slate-500 bg-white rounded-xl border border-slate-200">
            <Inbox className="w-10 h-10 mx-auto text-slate-300 mb-2" />
            <p className="font-medium text-slate-700">No notifications in this view</p>
            <p className="text-xs text-slate-400 mt-1">
              You are completely caught up with all operational events and responses.
            </p>
          </div>
        ) : (
          filteredNotifications.map((n) => {
            const targetTab = getTargetTabForNotification(n.category);
            return (
              <div
                key={n.id}
                className={`p-4 rounded-xl border transition shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                  n.is_read
                    ? "bg-white border-slate-200 opacity-80"
                    : "bg-indigo-50/20 border-indigo-200"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-1">
                    {!n.is_read ? (
                      <span className="w-2.5 h-2.5 rounded-full bg-indigo-600 block ring-4 ring-indigo-100" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4 text-slate-300" />
                    )}
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      {getCategoryBadge(n.category)}
                      <h4 className="text-sm font-semibold text-slate-900">{n.title}</h4>
                    </div>
                    <p className="text-xs text-slate-600">{n.message}</p>
                    <div className="text-[11px] text-slate-400">
                      {new Date(n.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                  {targetTab && onNavigateTab && (
                    <button
                      onClick={() => onNavigateTab(targetTab)}
                      className="flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg border border-indigo-200 transition"
                    >
                      View in Module
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  )}
                  {!n.is_read && (
                    <button
                      onClick={() => handleMarkAsRead(n.id)}
                      className="px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
                      title="Mark as read"
                    >
                      Dismiss
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
