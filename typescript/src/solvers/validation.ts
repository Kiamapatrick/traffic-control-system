import { Network } from '../models';

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