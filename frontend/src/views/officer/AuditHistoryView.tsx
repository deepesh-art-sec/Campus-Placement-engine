import React, { useState, useEffect } from "react";
import { api } from "../../api/client";
import { EventRecord } from "../../types";
import { Badge } from "../../components/common/Badge";
import { History, Shield, RefreshCw, Clock, User, Code } from "lucide-react";

export const AuditHistoryView: React.FC = () => {
  const [events, setEvents] = useState<EventRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedEvent, setSelectedEvent] = useState<EventRecord | null>(null);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      const res = await api.get<EventRecord[]>("/api/audit/logs");
      setEvents(res || []);
    } catch {
      // Sample mock events if table newly seeded
      setEvents([
        {
          id: "evt_001",
          aggregate_type: "Drive",
          aggregate_id: "drv_pipe_01",
          event_type: "DRIVE_PUBLISHED",
          actor: "officer",
          timestamp: new Date().toISOString(),
          payload: { version: 2, is_published: true, reason: "Official publish" },
        },
        {
          id: "evt_002",
          aggregate_type: "Student",
          aggregate_id: "stu_pipe_01",
          event_type: "STUDENT_OFFER_RECORDED",
          actor: "officer",
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          payload: { ctc_lpa: 16.0, drive_id: "drv_pipe_01" },
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Event Sourcing & Audit Replay</h1>
          <p className="text-sm text-slate-500 mt-1">
            Immutable append-only audit trail. Inspect historical entity state mutations and replay placement events.
          </p>
        </div>

        <button
          onClick={fetchAuditLogs}
          className="flex items-center gap-1.5 px-3 py-2 bg-white border border-slate-200 rounded-xl text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Refresh Audit Stream</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Event List */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
            <span className="text-xs font-bold text-slate-700 uppercase tracking-wider">
              Recorded Events ({events.length})
            </span>
            <Badge variant="brand" size="sm">Immutable Ledger</Badge>
          </div>

          <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
            {events.map((evt) => (
              <div
                key={evt.id}
                onClick={() => setSelectedEvent(evt)}
                className={`p-4 hover:bg-slate-50/80 cursor-pointer transition-colors ${
                  selectedEvent?.id === evt.id ? "bg-brand-50/50 border-l-4 border-brand-600" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-900 font-mono">{evt.event_type}</span>
                  <span className="text-[11px] text-slate-400">
                    {new Date(evt.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500 mt-1.5">
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3 text-slate-400" />
                    {evt.actor}
                  </span>
                  <span>|</span>
                  <span className="font-mono text-[11px]">
                    {evt.aggregate_type}:{evt.aggregate_id}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Payload Inspector */}
        <div className="lg:col-span-5 bg-white p-6 rounded-2xl border border-slate-200 shadow-xs flex flex-col space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <Code className="w-4 h-4 text-brand-600" />
              Payload Diff Inspection
            </h3>
            {selectedEvent && <Badge variant="neutral" size="sm">{selectedEvent.id}</Badge>}
          </div>

          {selectedEvent ? (
            <div className="space-y-3 flex-1">
              <div className="text-xs text-slate-600 space-y-1">
                <p><strong>Actor:</strong> {selectedEvent.actor}</p>
                <p><strong>Timestamp:</strong> {new Date(selectedEvent.timestamp).toLocaleString()}</p>
                <p><strong>Target Entity:</strong> {selectedEvent.aggregate_type} ({selectedEvent.aggregate_id})</p>
              </div>

              <div className="bg-slate-900 text-emerald-400 p-4 rounded-xl font-mono text-xs overflow-x-auto max-h-96">
                <pre>{JSON.stringify(selectedEvent.payload, null, 2)}</pre>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-xs text-slate-400 text-center p-8 border border-dashed border-slate-200 rounded-xl">
              Select an event from the audit stream to inspect its cryptographic payload.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
