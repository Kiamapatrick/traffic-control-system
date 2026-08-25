import { describe, it, expect } from 'vitest';
import { generateFourJunction, generateGridNetwork } from '../network/generator';
import { solveRREF, solveSimplex, validateNetwork } from '../solvers';

describe('RREF Solver', () => {
  it('should solve four junction network', () => {
    const network = generateFourJunction();
    const solution = solveRREF(network);

    expect(solution.method).toBe('rref');
    expect(Object.keys(solution.flows).length).toBe(5);
    expect(solution.isFeasible).toBe(true);
  });

  it('should produce non-negative flows', () => {
    const network = generateFourJunction();
    const solution = solveRREF(network);

    for (const flow of Object.values(solution.flows)) {
      expect(flow).toBeGreaterThanOrEqual(-1e-6);
    }
  });

  it('should respect capacity constraints', () => {
    const network = generateFourJunction();
    const solution = solveRREF(network);

    for (const road of network.roads) {
      const flow = solution.flows[road.id] ?? 0;
      expect(flow).toBeLessThanOrEqual(road.capacity + 1e-6);
    }
  });
});

describe('Simplex Solver', () => {
  it('should solve four junction network with min_cost', () => {
    const network = generateFourJunction();
    const solution = solveSimplex(network, 'min_cost');

    expect(solution.method).toBe('simplex');
    expect(solution.objective).toBe('min_cost');
    expect(solution.objectiveValue).toBeDefined();
    expect(solution.isFeasible).toBe(true);
  });

  it('should solve with different objectives', () => {
    const network = generateFourJunction();

    for (const obj of ['min_cost', 'max_throughput', 'min_travel_time', 'balance_load'] as const) {
      const solution = solveSimplex(network, obj);
      expect(solution.objective).toBe(obj);
      expect(solution.isFeasible).toBe(true);
    }
  });
});

describe('Network Validation', () => {
  it('should validate correct solution', () => {
    const network = generateFourJunction();
    const solution = solveRREF(network);
    const violations = validateNetwork(network, solution.flows);
    expect(violations.length).toBe(0);
  });

  it('should detect flow conservation violation', () => {
    const network = generateFourJunction();
    const badFlows = { x1: 100, x2: 0, x3: 0, x4: 0, x5: 0 };
    const violations = validateNetwork(network, badFlows);
    expect(violations.length).toBeGreaterThan(0);
  });

  it('should detect capacity violation', () => {
    const network = generateFourJunction();
    const badFlows = { x1: 200, x2: 0, x3: 0, x4: 0, x5: 0 };
    const violations = validateNetwork(network, badFlows);
    expect(violations.some(v => v.includes('exceeds capacity'))).toBe(true);
  });
});

describe('Network Generators', () => {
  it('should generate four junction', () => {
    const network = generateFourJunction();
    expect(network.junctions.length).toBe(4);
    expect(network.roads.length).toBe(5);
  });

  it('should generate grid network', () => {
    const network = generateGridNetwork(3, 4);
    expect(network.junctions.length).toBe(12);
    expect(network.roads.length).toBeGreaterThan(0);
  });
});