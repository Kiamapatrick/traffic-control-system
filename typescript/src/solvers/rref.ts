import { Network, FlowSolution, SolverMethod, Junction, Road } from '../models';

export function buildSystemMatrix(network: Network): { A: number[][]; b: number[]; roadIds: string[] } {
  const nJunctions = network.junctions.length;
  const nRoads = network.roads.length;

  const A: number[][] = Array(nJunctions).fill(null).map(() => Array(nRoads).fill(0));
  const b: number[] = Array(nJunctions).fill(0);

  const junctionToIdx: Record<string, number> = {};
  network.junctions.forEach((j, i) => { junctionToIdx[j.id] = i; });

  const roadToIdx: Record<string, number> = {};
  network.roads.forEach((r, i) => { roadToIdx[r.id] = i; });

  for (const road of network.roads) {
    const jSrc = junctionToIdx[road.source];
    const jTgt = junctionToIdx[road.target];
    const rIdx = roadToIdx[road.id];
    A[jSrc][rIdx] = -1.0;
    A[jTgt][rIdx] = 1.0;
  }

  for (const junction of network.junctions) {
    const idx = junctionToIdx[junction.id];
    b[idx] = junction.externalFlow;
  }

  const roadIds = network.roads.map(r => r.id);
  return { A, b, roadIds };
}

export function rrefSolve(A: number[][], b: number[], tol: number = 1e-10): { particular: number[]; nullspace: number[][]; pivotCols: number[] } {
  const m = A.length;
  const n = A[0].length;

  if (m !== b.length) {
    throw new Error(`Matrix shape mismatch: A=${m}x${n}, b=${b.length}`);
  }

  const M: number[][] = A.map((row, i) => [...row, b[i]]);

  const pivotCols: number[] = [];
  let row = 0;

  for (let col = 0; col < n && row < m; col++) {
    let maxRow = row;
    let maxVal = Math.abs(M[row][col]);
    for (let r = row + 1; r < m; r++) {
      const val = Math.abs(M[r][col]);
      if (val > maxVal) {
        maxVal = val;
        maxRow = r;
      }
    }

    if (maxVal < tol) continue;

    if (maxRow !== row) {
      [M[row], M[maxRow]] = [M[maxRow], M[row]];
    }

    const pivot = M[row][col];
    for (let c = col; c <= n; c++) {
      M[row][c] /= pivot;
    }

    for (let r = 0; r < m; r++) {
      if (r !== row) {
        const factor = M[r][col];
        if (Math.abs(factor) > tol) {
          for (let c = col; c <= n; c++) {
            M[r][c] -= factor * M[row][c];
          }
        }
      }
    }

    pivotCols.push(col);
    row++;
  }

  const rank = pivotCols.length;
  if (rank === 0) {
    return { particular: Array(n).fill(0), nullspace: [], pivotCols: [] };
  }

  const particular: number[] = Array(n).fill(0);
  for (let i = 0; i < rank; i++) {
    particular[pivotCols[i]] = M[i][n];
  }

  const freeCols = Array.from({ length: n }, (_, i) => i).filter(c => !pivotCols.includes(c));
  const nullity = freeCols.length;

  const nullspace: number[][] = Array(nullity).fill(null).map(() => Array(n).fill(0));
  for (let j = 0; j < nullity; j++) {
    const fc = freeCols[j];
    nullspace[j][fc] = 1.0;
    for (let i = 0; i < rank; i++) {
      nullspace[j][pivotCols[i]] = -M[i][fc];
    }
  }

  return { particular, nullspace: transpose(nullspace), pivotCols };
}

function transpose(matrix: number[][]): number[][] {
  if (matrix.length === 0) return [];
  return matrix[0].map((_, i) => matrix.map(row => row[i]));
}

function getCapacity(network: Network, roadId: string): number {
  const road = network.roads.find(r => r.id === roadId);
  return road ? road.capacity : Infinity;
}

export function solveRREF(network: Network): FlowSolution {
  const { A, b, roadIds } = buildSystemMatrix(network);
  const { particular, nullspace, pivotCols } = rrefSolve(A, b);

  const n = roadIds.length;
  let feasible = [...particular];

  if (nullspace.length > 0) {
    for (let i = 0; i < n; i++) {
      if (feasible[i] < 0) {
        for (let j = 0; j < nullspace[0].length; j++) {
          if (nullspace[i][j] < 0) {
            feasible[i] = 0;
            break;
          }
        }
      }
      const cap = getCapacity(network, roadIds[i]);
      if (feasible[i] > cap) {
        for (let j = 0; j < nullspace[0].length; j++) {
          if (nullspace[i][j] > 0) {
            feasible[i] = cap;
            break;
          }
        }
      }
    }
  } else {
    for (let i = 0; i < n; i++) {
      feasible[i] = Math.max(0, Math.min(feasible[i], getCapacity(network, roadIds[i])));
    }
  }

  const flows: Record<string, number> = {};
  for (let i = 0; i < roadIds.length; i++) {
    flows[roadIds[i]] = Math.max(0, feasible[i]);
  }

  const violations = validateNetwork(network, flows);

  return {
    flows,
    method: 'rref',
    objectiveValue: undefined,
    isFeasible: violations.length === 0,
    violations,
    metadata: {
      rank: pivotCols.length,
      nullity: nullspace.length,
      pivotColumns: pivotCols,
      particularSolution: particular,
    },
  };
}

export function validateNetwork(network: Network, flows: Record<string, number>): string[] {
  const violations: string[] = [];

  for (const junction of network.junctions) {
    let inflow = 0;
    let outflow = 0;
    for (const road of network.roads) {
      const flow = flows[road.id] ?? 0;
      if (road.target === junction.id) inflow += flow;
      if (road.source === junction.id) outflow += flow;
    }
    const netFlow = inflow - outflow;
    if (Math.abs(netFlow - junction.externalFlow) > 1e-6) {
      violations.push(`Junction ${junction.id}: net flow ${netFlow.toFixed(2)} != external ${junction.externalFlow}`);
    }
  }

  for (const road of network.roads) {
    const flow = flows[road.id] ?? 0;
    if (flow < -1e-6) {
      violations.push(`Road ${road.id}: negative flow ${flow.toFixed(2)}`);
    }
    if (flow > road.capacity + 1e-6) {
      violations.push(`Road ${road.id}: flow ${flow.toFixed(2)} exceeds capacity ${road.capacity}`);
    }
  }

  return violations;
}