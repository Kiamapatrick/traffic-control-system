'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LineChart, Line } from 'recharts';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const SOLVERS = [
  { id: 'rref', name: 'RREF (Python)', lang: 'Python' },
  { id: 'lp', name: 'LP Simplex (Python)', lang: 'Python' },
  { id: 'rref-ts', name: 'RREF (TypeScript)', lang: 'TypeScript' },
  { id: 'simplex-ts', name: 'Simplex (TypeScript)', lang: 'TypeScript' },
  { id: 'rref-rs', name: 'RREF (Rust)', lang: 'Rust' },
  { id: 'simplex-rs', name: 'Simplex (Rust)', lang: 'Rust' },
];

const LANGS = ['Python', 'TypeScript', 'Rust'];

export default function ComparePage() {
  const [results, setResults] = useState<Record<string, any>>({});
  const [benchmark, setBenchmark] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [networkSize, setNetworkSize] = useState(3);

  const generateNetwork = (size: number) => {
    const junctions = [];
    const roads = [];
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        const id = `J_${r}_${c}`;
        junctions.push({ id, position: [c * 100, r * 100], junctionType: 'normal', externalFlow: 0 });
      }
    }
    for (let r = 0; r < size; r++) {
      for (let c = 0; c < size; c++) {
        const id = `J_${r}_${c}`;
        if (c + 1 < size) {
          const target = `J_${r}_${c + 1}`;
          roads.push({ id: `R_${id}_E`, source: id, target, capacity: 1000, length: 100, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 2 });
          roads.push({ id: `R_${target}_W`, source: target, target: id, capacity: 1000, length: 100, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 2 });
        }
        if (r + 1 < size) {
          const target = `J_${r + 1}_${c}`;
          roads.push({ id: `R_${id}_S`, source: id, target, capacity: 1000, length: 100, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 2 });
          roads.push({ id: `R_${target}_N`, source: target, target: id, capacity: 1000, length: 100, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 2 });
        }
      }
    }
    junctions[0].externalFlow = 500;
    junctions[0].junctionType = 'source';
    junctions[size * size - 1].externalFlow = -500;
    junctions[size * size - 1].junctionType = 'sink';
    return { junctions, roads, metadata: {} };
  };

  const runSolver = async (solverId: string, network: any) => {
    setLoading(prev => ({ ...prev, [solverId]: true }));
    try {
      const method = solverId.includes('lp') || solverId.includes('simplex') ? 'lp' : 'rref';
      const response = await axios.post(`${API_BASE}/solve`, {
        network,
        method,
        objective: 'min_cost',
      }, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
      });
      setResults(prev => ({ ...prev, [solverId]: response.data }));
    } catch (err) {
      setResults(prev => ({ ...prev, [solverId]: { error: err.message } }));
    } finally {
      setLoading(prev => ({ ...prev, [solverId]: false }));
    }
  };

  const runBenchmark = async () => {
    const network = generateNetwork(networkSize);
    setBenchmark({});
    for (const solver of SOLVERS) {
      setLoading(prev => ({ ...prev, [solver.id]: true }));
      const times: number[] = [];
      for (let i = 0; i < 5; i++) {
        try {
          const start = performance.now();
          await axios.post(`${API_BASE}/solve`, {
            network,
            method: solver.id.includes('lp') || solver.id.includes('simplex') ? 'lp' : 'rref',
            objective: 'min_cost',
          }, {
            headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
          });
          times.push(performance.now() - start);
        } catch (e) {
          times.push(NaN);
        }
      }
      const valid = times.filter(t => !isNaN(t));
      setBenchmark(prev => ({
        ...prev,
        [solver.id]: {
          mean: valid.reduce((a, b) => a + b, 0) / valid.length,
          min: Math.min(...valid),
          max: Math.max(...valid),
        },
      }));
      setLoading(prev => ({ ...prev, [solver.id]: false }));
    }
  };

  const handleRunAll = () => {
    const network = generateNetwork(networkSize);
    SOLVERS.forEach(s => runSolver(s.id, network));
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center gap-4">
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Solver Comparison</h1>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-600 dark:text-gray-400">Grid Size:</label>
            <select
              value={networkSize}
              onChange={e => setNetworkSize(parseInt(e.target.value))}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-sm"
            >
              <option value={2}>2x2 (4 junctions)</option>
              <option value={3}>3x3 (9 junctions)</option>
              <option value={4}>4x4 (16 junctions)</option>
              <option value={5}>5x5 (25 junctions)</option>
            </select>
          </div>
          <button onClick={handleRunAll} disabled={Object.values(loading).some(v => v)} className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50">
            Run All Solvers
          </button>
          <button onClick={runBenchmark} disabled={Object.values(loading).some(v => v)} className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50">
            Benchmark (5 runs)
          </button>
        </div>
      </header>

      <div className="flex-1 flex max-w-7xl mx-auto w-full p-4 gap-8 overflow-hidden">
        <div className="flex-1 min-w-0">
          <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${SOLVERS.length}, minmax(200px, 1fr))` }}>
            {SOLVERS.map(solver => {
              const result = results[solver.id];
              const bench = benchmark[solver.id];
              return (
                <div key={solver.id} className="bg-white dark:bg-gray-800 rounded-xl shadow-md p-4 border border-gray-200 dark:border-gray-700 min-w-[200px]">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold">{solver.name}</h3>
                    <span className={`px-2 py-0.5 text-xs rounded-full ${
                      solver.lang === 'Python' ? 'bg-blue-100 text-blue-800' :
                      solver.lang === 'TypeScript' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-orange-100 text-orange-800'
                    }`}>{solver.lang}</span>
                  </div>
                  {loading[solver.id] && <div className="text-sm text-gray-500 animate-pulse">Running...</div>}
                  {result?.error && <div className="text-sm text-red-600">Error: {result.error}</div>}
                  {result?.solution && (
                    <div className="space-y-1 text-sm">
                      <p>Time: {result.solve_time_ms?.toFixed(1)}ms</p>
                      <p>Feasible: {result.solution.is_feasible ? '✓' : '✗'}</p>
                      <p>Obj: {result.solution.objective_value?.toFixed(2) ?? 'N/A'}</p>
                    </div>
                  )}
                  {bench?.mean && (
                    <div className="mt-2 pt-2 border-t border-gray-200 dark:border-gray-700 text-sm text-gray-600 dark:text-gray-400">
                      <p>Avg: {bench.mean.toFixed(1)}ms</p>
                      <p>Range: {bench.min.toFixed(1)} - {bench.max.toFixed(1)}ms</p>
                    </div>
                  )}
                  {!result?.solution && !loading[solver.id] && !result?.error && (
                    <div className="text-sm text-gray-500">Not run yet</div>
                  )}
                </div>
              );
            })}
          </div>

          {Object.keys(results).length > 0 && (
            <div className="mt-8">
              <h2 className="text-xl font-bold mb-4">Flow Comparison</h2>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart
                  data={(() => {
                    const roadIds = new Set<string>();
                    Object.values(results).forEach(r => r.solution?.flows && Object.keys(r.solution.flows).forEach(k => roadIds.add(k)));
                    return Array.from(roadIds).map(road => {
                      const row: any = { road };
                      SOLVERS.forEach(s => {
                        row[s.id] = results[s.id]?.solution?.flows?.[road] ?? 0;
                      });
                      return row;
                    });
                  })()}
                  layout="vertical"
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="road" width={60} />
                  <Tooltip />
                  {SOLVERS.map((s, i) => (
                    <Bar key={s.id} dataKey={s.id} radius={[0, 4, 4, 0]} name={s.name} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {Object.keys(benchmark).length > 0 && (
            <div className="mt-8">
              <h2 className="text-xl font-bold mb-4">Benchmark Results</h2>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart
                  data={SOLVERS.map(s => ({
                    name: s.name,
                    mean: benchmark[s.id]?.mean ?? 0,
                    min: benchmark[s.id]?.min ?? 0,
                    max: benchmark[s.id]?.max ?? 0,
                    lang: s.lang,
                  }))}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="category" dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="mean" name="Mean (ms)">
                    {SOLVERS.map((s, i) => (
                      <Cell key={s.id} fill={
                        s.lang === 'Python' ? '#3b82f6' :
                        s.lang === 'TypeScript' ? '#f59e0b' : '#f97316'
                      } />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}