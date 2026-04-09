"use client";

type AuditSummary = {
  audit_id: string;
  timestamp: string;
  decision_type: string;
  symbol: string;
  status: string;
  cycle_id: string | null;
};

export default function DecisionAuditPanel({
  entries,
  selectedAuditId,
  onSelect,
}: {
  entries: AuditSummary[] | null;
  selectedAuditId: string | null;
  onSelect: (auditId: string) => void;
}) {
  if (!entries) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading decision audit trail...</div>;
  }

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Decision Audit Trail</h3>
        <span className="text-xs text-slate-300">Click a row to replay</span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Time</th>
              <th className="px-2 py-1">Type</th>
              <th className="px-2 py-1">Symbol</th>
              <th className="px-2 py-1">Status</th>
              <th className="px-2 py-1">Audit ID</th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 && (
              <tr>
                <td className="px-2 py-2 text-slate-400" colSpan={5}>
                  No audit records yet.
                </td>
              </tr>
            )}
            {entries.slice(0, 8).map((item) => {
              const selected = selectedAuditId === item.audit_id;
              return (
                <tr
                  key={item.audit_id}
                  className={`cursor-pointer border-t border-terminal-line ${selected ? "bg-terminal-accent/10" : "hover:bg-white/5"}`}
                  onClick={() => onSelect(item.audit_id)}
                >
                  <td className="px-2 py-2 text-slate-400">{new Date(item.timestamp).toLocaleTimeString()}</td>
                  <td className="px-2 py-2">{item.decision_type}</td>
                  <td className="px-2 py-2">{item.symbol}</td>
                  <td className={`px-2 py-2 ${item.status === "ACCEPTED" ? "text-terminal-bull" : "text-terminal-bear"}`}>
                    {item.status}
                  </td>
                  <td className="px-2 py-2 text-[10px] text-slate-400">{item.audit_id.slice(0, 10)}...</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
