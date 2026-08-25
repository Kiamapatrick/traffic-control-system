'use client';

import { useState, useCallback } from 'react';
import ReactFlow, {
  addEdge,
  Connection,
  Node,
  Edge,
  NodeTypes,
  EdgeTypes,
  useReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Handle, Position } from 'reactflow';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface JunctionNode extends Node {
  data: {
    label: string;
    externalFlow: number;
  };
}

interface RoadEdge extends Edge {
  data: {
    flow?: number;
    capacity: number;
    label?: string;
  };
}

const initialNodes: JunctionNode[] = [
  { id: 'A', type: 'junction', position: { x: 200, y: 100 }, data: { label: 'A', externalFlow: 80 } },
  { id: 'B', type: 'junction', position: { x: 500, y: 100 }, data: { label: 'B', externalFlow: -30 } },
  { id: 'C', type: 'junction', position: { x: 500, y: 400 }, data: { label: 'C', externalFlow: 50 } },
  { id: 'D', type: 'junction', position: { x: 200, y: 400 }, data: { label: 'D', externalFlow: -60 } },
];

const initialEdges: RoadEdge[] = [
  { id: 'x1', source: 'A', target: 'B', type: 'road', data: { capacity: 100 }, animated: true },
  { id: 'x2', source: 'B', target: 'C', type: 'road', data: { capacity: 100 }, animated: true },
  { id: 'x3', source: 'C', target: 'D', type: 'road', data: { capacity: 100 }, animated: true },
  { id: 'x4', source: 'D', target: 'A', type: 'road', data: { capacity: 100 }, animated: true },
  { id: 'x5', source: 'B', target: 'D', type: 'road', data: { capacity: 100 }, animated: true },
];

const nodeTypes: NodeTypes = {
  junction: JunctionNodeComponent,
};

const edgeTypes: EdgeTypes = {
  road: RoadEdgeComponent,
};

function JunctionNodeComponent({ data }: { data: { label: string; externalFlow: number } }) {
  const isSource = data.externalFlow > 0;
  const isSink = data.externalFlow < 0;

  return (
    <div className="flex flex-col items-center gap-1">
      <Handle type="target" position={Position.Top} className="w-2 h-2 bg-gray-400" />
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 bg-gray-400" />
      <div
        className={`w-20 h-20 rounded-full flex items-center justify-center font-bold text-lg border-2 transition-all ${
          isSource ? 'bg-green-100 border-green-500 text-green-700 dark:bg-green-900 dark:border-green-400 dark:text-green-200'
          : isSink ? 'bg-red-100 border-red-500 text-red-700 dark:bg-red-900 dark:border-red-400 dark:text-red-200'
          : 'bg-blue-100 border-blue-500 text-blue-700 dark:bg-blue-900 dark:border-blue-400 dark:text-blue-200'
        }`}
      >
        {data.label}
      </div>
      <div className="text-xs font-mono">
        {data.externalFlow > 0 ? '+' : ''}{data.externalFlow}
      </div>
    </div>
  );
}

function RoadEdgeComponent({ data }: { data: { flow?: number; capacity: number; label?: string } }) {
  const flow = data.flow ?? 0;
  const capacity = data.capacity;
  const utilization = capacity > 0 ? flow / capacity : 0;
  const color = utilization > 0.8 ? '#ef4444' : utilization > 0.5 ? '#f59e0b' : '#22c55e';
  const width = Math.max(2, 2 + utilization * 6);

  return (
    <>
      <path
        stroke={color}
        strokeWidth={width}
        fill="none"
        style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.1))' }}
      />
      {data.label && (
        <text
          dominantBaseline="central"
          textAnchor="middle"
          fontSize="10"
          fontWeight="bold"
          fill={color}
          paintOrder="stroke"
          stroke="white"
          strokeWidth="3"
        >
          {data.label}: {flow.toFixed(0)}
        </text>
      )}
    </>
  );
}

export default function SolverPage() {
  const [nodes, setNodes] = useState<JunctionNode[]>(initialNodes);
  const [edges, setEdges] = useState<RoadEdge[]>(initialEdges);
  const [method, setMethod] = useState<'rref' | 'lp' | 'milp' | 'max-flow'>('rref');
  const [objective, setObjective] = useState<'min_cost' | 'max_throughput' | 'min_travel_time' | 'balance_load'>('min_cost');
  const [source, setSource] = useState('A');
  const [sink, setSink] = useState('C');
  const [results, setResults] = useState<Record<string, number> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [solveTime, setSolveTime] = useState<number | null>(null);

  const { fitView } = useReactFlow();

  const onConnect = useCallback((params: Connection) => {
    if (params.source === params.target) return;
    setEdges((eds) => addEdge({ ...params, type: 'road', animated: true, data: { capacity: 100 } }, eds));
  }, []);

  const onNodesChange = useCallback((changes: any[]) => {
    setNodes((nds) => {
      // Simplified - in real app use applyNodeChanges
      return nds;
    });
  }, []);

  const onEdgesChange = useCallback((changes: any[]) => {
    setEdges((eds) => {
      // Simplified - in real app use applyEdgeChanges
      return eds;
    });
  }, []);

  const buildNetwork = useCallback(() => {
    const junctions = nodes.map(n => ({
      id: n.id,
      position: [n.position.x, n.position.y] as [number, number],
      junctionType: n.data.externalFlow > 0 ? 'source' : n.data.externalFlow < 0 ? 'sink' : 'normal',
      externalFlow: n.data.externalFlow,
    }));

    const roads = edges.map(e => ({
      id: e.id,
      source: e.source,
      target: e.target,
      capacity: e.data.capacity,
      length: Math.hypot(
        nodes.find(n => n.id === e.target)!.position.x - nodes.find(n => n.id === e.source)!.position.x,
        nodes.find(n => n.id === e.target)!.position.y - nodes.find(n => n.id === e.source)!.position.y
      ) / 100,
      flow: 0,
      costPerUnit: 1,
      freeFlowSpeed: 50,
      lanes: 1,
    }));

    return { junctions, roads, metadata: {} };
  }, [nodes, edges]);

  const handleSolve = async () => {
    setLoading(true);
    setError(null);
    setResults(null);

    const network = buildNetwork();
    const params = method === 'max-flow' ? { source, sink } : {};

    try {
      const response = await axios.post(`${API_BASE}/solve`, {
        network,
        method,
        objective: method === 'lp' ? objective : undefined,
        parameters: params,
      }, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
      });

      setResults(response.data.solution.flows);
      setSolveTime(response.data.solve_time_ms);

      // Update edge data with flows
      setEdges(eds => eds.map(e => ({
        ...e,
        data: { ...e.data, flow: response.data.solution.flows[e.id] ?? 0, label: e.id },
        animated: (response.data.solution.flows[e.id] ?? 0) > 0,
      })));

      fitView();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAddJunction = () => {
    const newId = String.fromCharCode(65 + nodes.length);
    setNodes(nds => [...nds, {
      id: newId,
      type: 'junction',
      position: { x: 100 + (nodes.length % 4) * 150, y: 100 + Math.floor(nodes.length / 4) * 150 },
      data: { label: newId, externalFlow: 0 },
    }]);
  };

  const handleLoadExample = (example: string) => {
    if (example === 'four-junction') {
      setNodes(initialNodes);
      setEdges(initialEdges);
    }
  };

  const flowData = results
    ? Object.entries(results).map(([road, flow]) => {
        const edge = edges.find(e => e.id === road);
        return { road, flow, capacity: edge?.data.capacity ?? 0 };
      })
    : [];

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center gap-4">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Network Solver</h1>
          <div className="flex-1" />
          <select
            value={method}
            onChange={e => setMethod(e.target.value as any)}
            className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
          >
            <option value="rref">RREF (Gaussian Elimination)</option>
            <option value="lp">Linear Programming</option>
            <option value="milp">MILP (Discrete)</option>
            <option value="max-flow">Max Flow</option>
          </select>

          {method === 'lp' && (
            <select
              value={objective}
              onChange={e => setObjective(e.target.value as any)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
            >
              <option value="min_cost">Min Cost</option>
              <option value="max_throughput">Max Throughput</option>
              <option value="min_travel_time">Min Travel Time</option>
              <option value="balance_load">Balance Load</option>
            </select>
          )}

          {method === 'max-flow' && (
            <div className="flex items-center gap-2">
              <select value={source} onChange={e => setSource(e.target.value)} className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm">
                {nodes.map(n => <option key={n.id} value={n.id}>{n.data.label}</option>)}
              </select>
              <span className="text-gray-400">→</span>
              <select value={sink} onChange={e => setSink(e.target.value)} className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm">
                {nodes.map(n => <option key={n.id} value={n.id}>{n.data.label}</option>)}
              </select>
            </div>
          )}

          <button
            onClick={handleSolve}
            disabled={loading}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Solving...' : 'Solve'}
          </button>

          <button
            onClick={handleAddJunction}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-white rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            + Junction
          </button>

          <select onChange={e => handleLoadExample(e.target.value)} className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm">
            <option value="">Load Example</option>
            <option value="four-junction">Four Junction</option>
          </select>
        </div>
      </header>

      {error && (
        <div className="mx-4 mt-4 p-4 bg-red-100 dark:bg-red-900 border border-red-400 dark:border-red-700 rounded-lg text-red-800 dark:text-red-200">
          {error}
        </div>
      )}

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 min-w-0">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            fitView
            attributionPosition="bottom-right"
          >
            <Background color="#e5e7eb" gap={20} />
            <Controls />
            <MiniMap />
            <Panel position="bottom-left">
              <div className="p-3 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 text-sm">
                <p className="font-medium">Controls</p>
                <p className="text-gray-600 dark:text-gray-400 mt-1">Drag nodes to move</p>
                <p className="text-gray-600 dark:text-gray-400">Drag handles to connect</p>
                <p className="text-gray-600 dark:text-gray-400">Click Solve to compute flows</p>
              </div>
            </Panel>
          </ReactFlow>
        </div>

        <div className="w-80 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 overflow-y-auto">
          <h3 className="font-semibold mb-3">Results</h3>
          {results && (
            <>
              <div className="mb-4 text-sm">
                <p>Solve time: {solveTime?.toFixed(1)}ms</p>
                <p>Method: {method.toUpperCase()}</p>
                {method === 'lp' && <p>Objective: {objective}</p>}
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={flowData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="road" width={60} />
                  <Tooltip formatter={(value: number) => [value.toFixed(1), 'veh/h']} />
                  <Bar dataKey="flow" radius={[0, 4, 4, 0]}>
                    {flowData.map((_, i) => (
                      <Cell key={i} fill={flowData[i].flow / flowData[i].capacity > 0.8 ? '#ef4444' : '#3b82f6'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="mt-4 max-h-60 overflow-y-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-gray-700">
                      <th className="text-left py-1">Road</th>
                      <th className="text-right py-1">Flow</th>
                      <th className="text-right py-1">Capacity</th>
                      <th className="text-right py-1">Utilization</th>
                    </tr>
                  </thead>
                  <tbody>
                    {flowData.map(d => (
                      <tr key={d.road} className="border-b border-gray-100 dark:border-gray-800">
                        <td className="py-1 font-mono">{d.road}</td>
                        <td className="text-right py-1">{d.flow.toFixed(1)}</td>
                        <td className="text-right py-1">{d.capacity}</td>
                        <td className="text-right py-1">
                          <span className={d.flow / d.capacity > 0.8 ? 'text-red-600' : 'text-green-600'}>
                            {(d.flow / d.capacity * 100).toFixed(1)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          {!results && (
            <p className="text-gray-500 dark:text-gray-400 text-center py-8">Click Solve to see results</p>
          )}
        </div>
      </div>
    </div>
  );
}