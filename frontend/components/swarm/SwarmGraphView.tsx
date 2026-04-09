"use client";

import { useMemo } from "react";

import type { SwarmAgentSignal } from "../../types/swarm";

type GraphNode = {
  id: string;
  x: number;
  y: number;
  confidence: number;
  action: "BUY" | "SELL" | "HOLD";
};

type GraphEdge = {
  source: string;
  target: string;
  agree: boolean;
};

type Props = {
  signals: SwarmAgentSignal[];
};

const NODE_COLORS: Record<string, string> = {
  BUY: "#22c55e",
  SELL: "#ef4444",
  HOLD: "#94a3b8",
};

export default function SwarmGraphView({ signals }: Props) {
  const { nodes, edges } = useMemo(() => {
    const radius = 120;
    const centerX = 180;
    const centerY = 145;

    const ns: GraphNode[] = signals.map((sig, idx) => {
      const angle = (idx / Math.max(signals.length, 1)) * Math.PI * 2;
      return {
        id: sig.agent_name,
        x: centerX + Math.cos(angle) * radius,
        y: centerY + Math.sin(angle) * radius,
        confidence: sig.confidence,
        action: sig.action,
      };
    });

    const es: GraphEdge[] = [];
    for (let i = 0; i < signals.length; i += 1) {
      for (let j = i + 1; j < signals.length; j += 1) {
        es.push({
          source: signals[i].agent_name,
          target: signals[j].agent_name,
          agree: signals[i].action === signals[j].action,
        });
      }
    }

    return { nodes: ns, edges: es };
  }, [signals]);

  const nodeMap = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  if (signals.length === 0) {
    return <div className="rounded border border-terminal-line bg-black/20 p-3 text-xs text-slate-400">No agent signals yet.</div>;
  }

  return (
    <div className="panel rounded-xl p-4">
      <h3 className="mb-3 text-sm font-semibold text-terminal-accent">Agent Battlefield</h3>
      <div className="overflow-x-auto">
        <svg width="360" height="290" viewBox="0 0 360 290" className="mx-auto">
          {edges.map((edge) => {
            const s = nodeMap.get(edge.source);
            const t = nodeMap.get(edge.target);
            if (!s || !t) {
              return null;
            }
            return (
              <line
                key={`${edge.source}-${edge.target}`}
                x1={s.x}
                y1={s.y}
                x2={t.x}
                y2={t.y}
                stroke={edge.agree ? "#34d399" : "#f59e0b"}
                strokeWidth={edge.agree ? 1.8 : 1.4}
                strokeDasharray={edge.agree ? "0" : "5 4"}
                opacity={0.8}
              />
            );
          })}

          {nodes.map((node) => {
            const r = 12 + node.confidence * 16;
            return (
              <g key={node.id}>
                <circle cx={node.x} cy={node.y} r={r} fill={NODE_COLORS[node.action]} opacity={0.22} />
                <circle cx={node.x} cy={node.y} r={Math.max(7, r - 4)} fill={NODE_COLORS[node.action]} />
                <text
                  x={node.x}
                  y={node.y + r + 14}
                  textAnchor="middle"
                  fontSize="10"
                  fill="#cbd5e1"
                >
                  {node.id.replace("_agent", "")}
                </text>
                <text
                  x={node.x}
                  y={node.y + 4}
                  textAnchor="middle"
                  fontSize="9"
                  fontWeight={700}
                  fill="#020617"
                >
                  {Math.round(node.confidence * 100)}%
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-2 text-xs text-slate-300 md:grid-cols-2">
        <div className="rounded border border-terminal-line bg-black/20 p-2">Solid edge = agreement</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">Dashed edge = disagreement</div>
      </div>
    </div>
  );
}
