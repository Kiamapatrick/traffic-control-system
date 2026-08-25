import { Network, FlowSolution, SolverMethod, OptimizationObjective, Road } from '../models';
import { validateNetwork } from './validation';

export function solveSimplex(network: Network, objective: OptimizationObjective = 'min_cost'): FlowSolution {
  const nJunctions = network.junctions.length;
  const nRoads = network.roads.length;

  if (nRoads === 0) {
    return {
      flows: {},
      method: 'simplex',
      objective,
      objectiveValue: undefined,
      isFeasible: false,
      violations: ['Network has no roads'],
      metadata: {},
    };
  }

  const tableau = buildTableau(network, objective);
  const basis = Array.from({ length: nJunctions }, (_, i) => i);

  let iterations = 0;
  const maxIterations = 1000;

  while (iterations < maxIterations) {
    const entering = findEnteringVariable(tableau);
    if (entering === null) break;

    const leaving = findLeavingVariable(tableau, entering);
    if (leaving === null) {
      const flows = extractFlows(tableau, network, basis);
      return {
        flows,
        method: 'simplex',
        objective,
        objectiveValue: tableau[nJunctions][nJunctions + nRoads],
        isFeasible: false,
        violations: ['Problem is unbounded'],
        metadata: { iterations },
      };
    }

    pivot(tableau, leaving, entering);
    basis[leaving] = entering;
    iterations++;
  }

  const flows = extractFlows(tableau, network, basis);
  const violations = validateNetwork(network, flows);

  return {
    flows,
    method: 'simplex',
    objective,
    objectiveValue: -tableau[nJunctions][nJunctions + nRoads],
    isFeasible: violations.length === 0,
    violations,
    metadata: { iterations },
  };
}

function buildTableau(network: Network, objective: OptimizationObjective): number[][] {
  const nJunctions = network.junctions.length;
  const nRoads = network.roads.length;

  const junctionToIdx: Record<string, number> = {};
  network.junctions.forEach((j, i) => { junctionToIdx[j.id] = i; });

  const roadToIdx: Record<string, number> = {};
  network.roads.forEach((r, i) => { roadToIdx[r.id] = i; });

  const tableau: number[][] = Array(nJunctions + 1)
    .fill(null)
    .map(() => Array(nJunctions + nRoads + 1).fill(0));

  for (const road of network.roads) {
    const jSrc = junctionToIdx[road.source];
    const jTgt = junctionToIdx[road.target];
    const rIdx = roadToIdx[road.id];
    tableau[jSrc][nJunctions + rIdx] = -1.0;
    tableau[jTgt][nJunctions + rIdx] = 1.0;
  }

  for (let i = 0; i < nJunctions; i++) {
    tableau[i][nJunctions + nRoads] = network.junctions[i].externalFlow;
  }

  for (const road of network.roads) {
    const rIdx = roadToIdx[road.id];
    switch (objective) {
      case 'min_cost':
        tableau[nJunctions][nJunctions + rIdx] = road.costPerUnit;
        break;
      case 'max_throughput':
        tableau[nJunctions][nJunctions + rIdx] = -1.0;
        break;
      case 'min_travel_time':
        tableau[nJunctions][nJunctions + rIdx] = road.length / road.freeFlowSpeed;
        break;
      case 'balance_load':
        tableau[nJunctions][nJunctions + rIdx] = Math.pow(1.0 / road.capacity, 2);
        break;
    }
  }

  for (let i = 0; i < nJunctions; i++) {
    tableau[nJunctions][i] = -tableau[i].reduce((sum, val) => sum + val, 0);
  }
  tableau[nJunctions][nJunctions + nRoads] = -tableau.slice(0, nJunctions)
    .reduce((sum, row) => sum + row[nJunctions + nRoads], 0);

  return tableau;
}

function findEnteringVariable(tableau: number[][]): number | null {
  const lastRow = tableau.length - 1;
  const n = tableau[0].length - 1;
  let maxVal = 0;
  let entering = null;
  for (let j = 0; j < n; j++) {
    if (tableau[lastRow][j] > maxVal) {
      maxVal = tableau[lastRow][j];
      entering = j;
    }
  }
  return entering;
}

function findLeavingVariable(tableau: number[][], entering: number): number | null {
  const nRows = tableau.length - 1;
  const rhsCol = tableau[0].length - 1;
  let minRatio = Infinity;
  let leaving = null;
  for (let i = 0; i < nRows; i++) {
    const coeff = tableau[i][entering];
    if (coeff > 1e-9) {
      const ratio = tableau[i][rhsCol] / coeff;
      if (ratio < minRatio) {
        minRatio = ratio;
        leaving = i;
      }
    }
  }
  return leaving;
}

function pivot(tableau: number[][], leaving: number, entering: number): void {
  const pivotVal = tableau[leaving][entering];
  const nCols = tableau[0].length;

  for (let j = 0; j < nCols; j++) {
    tableau[leaving][j] /= pivotVal;
  }

  for (let i = 0; i < tableau.length; i++) {
    if (i !== leaving) {
      const factor = tableau[i][entering];
      if (Math.abs(factor) > 1e-9) {
        for (let j = 0; j < nCols; j++) {
          tableau[i][j] -= factor * tableau[leaving][j];
        }
      }
    }
  }
}

function extractFlows(tableau: number[][], network: Network, basis: number[]): Record<string, number> {
  const nJunctions = network.junctions.length;
  const flows: Record<string, number> = {};

  const roadToIdx: Record<string, number> = {};
  network.roads.forEach((r, i) => { roadToIdx[r.id] = i; });

  for (let i = 0; i < basis.length; i++) {
    const basicVar = basis[i];
    if (basicVar >= nJunctions) {
      const roadIdx = basicVar - nJunctions;
      for (const [roadId, idx] of Object.entries(roadToIdx)) {
        if (idx === roadIdx) {
          flows[roadId] = Math.max(0, tableau[i][nJunctions + network.roads.length]);
          break;
        }
      }
    }
  }

  for (const road of network.roads) {
    if (!(road.id in flows)) flows[road.id] = 0;
  }

  return flows;
}