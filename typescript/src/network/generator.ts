import { Network, Junction, Road } from '../models';

export function generateFourJunction(): Network {
  return {
    junctions: [
      { id: 'A', position: [200, 600], junctionType: 'source', externalFlow: 80 },
      { id: 'B', position: [800, 600], junctionType: 'sink', externalFlow: -30 },
      { id: 'C', position: [800, 200], junctionType: 'source', externalFlow: 50 },
      { id: 'D', position: [200, 200], junctionType: 'sink', externalFlow: -60 },
    ],
    roads: [
      { id: 'x1', source: 'A', target: 'B', capacity: 100, length: 6, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 1 },
      { id: 'x2', source: 'B', target: 'C', capacity: 100, length: 4, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 1 },
      { id: 'x3', source: 'C', target: 'D', capacity: 100, length: 6, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 1 },
      { id: 'x4', source: 'D', target: 'A', capacity: 100, length: 4, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 1 },
      { id: 'x5', source: 'B', target: 'D', capacity: 100, length: 6.3, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 1 },
    ],
    metadata: {},
  };
}

export function generateGridNetwork(rows: number, cols: number, spacing = 100): Network {
  const junctions: Junction[] = [];
  const roads: Road[] = [];

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const id = `J_${r}_${c}`;
      junctions.push({
        id,
        position: [c * spacing, r * spacing],
        junctionType: 'normal',
        externalFlow: 0,
      });
    }
  }

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const id = `J_${r}_${c}`;
      if (c + 1 < cols) {
        const target = `J_${r}_${c + 1}`;
        roads.push({
          id: `R_${id}_E`, source: id, target,
          capacity: 1000, length: spacing, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 2,
        });
        roads.push({
          id: `R_${target}_W`, source: target, target: id,
          capacity: 1000, length: spacing, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 2,
        });
      }
      if (r + 1 < rows) {
        const target = `J_${r + 1}_${c}`;
        roads.push({
          id: `R_${id}_S`, source: id, target,
          capacity: 1000, length: spacing, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 2,
        });
        roads.push({
          id: `R_${target}_N`, source: target, target: id,
          capacity: 1000, length: spacing, flow: 0, costPerUnit: 1, freeFlowSpeed: 50, lanes: 2,
        });
      }
    }
  }

  return { junctions, roads, metadata: {} };
}