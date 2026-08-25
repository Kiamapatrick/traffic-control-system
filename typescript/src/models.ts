export interface Junction {
  id: string;
  position: [number, number];
  junctionType: JunctionType;
  externalFlow: number;
}

export type JunctionType = 'normal' | 'source' | 'sink';

export interface Road {
  id: string;
  source: string;
  target: string;
  capacity: number;
  length: number;
  flow: number;
  costPerUnit: number;
  freeFlowSpeed: number;
  lanes: number;
}

export interface Network {
  junctions: Junction[];
  roads: Road[];
  metadata: Record<string, unknown>;
}

export type SolverMethod = 'rref' | 'simplex' | 'max-flow' | 'dinic';

export type OptimizationObjective = 'min_cost' | 'max_throughput' | 'min_travel_time' | 'balance_load';

export interface FlowSolution {
  flows: Record<string, number>;
  method: SolverMethod;
  objective?: OptimizationObjective;
  objectiveValue?: number;
  isFeasible: boolean;
  violations: string[];
  metadata: Record<string, unknown>;
}

export interface SolveRequest {
  network: Network;
  method: SolverMethod;
  objective?: OptimizationObjective;
  parameters: Record<string, unknown>;
}