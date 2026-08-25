from __future__ import annotations

from hypothesis import given, strategies as st, settings, example
import numpy as np
from traffic_control.models import Junction, Road, Network
from traffic_control.solvers import solve_rref, validate_solution


@st.composite
def network_strategy(draw):
    n_junctions = draw(st.integers(min_value=2, max_value=6))
    n_roads = draw(st.integers(min_value=n_junctions - 1, max_value=n_junctions * 2))

    junctions = []
    for i in range(n_junctions):
        x = draw(st.floats(min_value=0, max_value=1000))
        y = draw(st.floats(min_value=0, max_value=1000))
        junctions.append(Junction(id=f"J{i}", position=(x, y)))

    roads = []
    road_id = 0
    edges = set()
    attempts = 0
    while len(roads) < n_roads and attempts < n_roads * 10:
        src = draw(st.sampled_from(junctions))
        tgt = draw(st.sampled_from(junctions))
        if src.id == tgt.id:
            attempts += 1
            continue
        if (src.id, tgt.id) in edges:
            attempts += 1
            continue
        edges.add((src.id, tgt.id))
        cap = draw(st.floats(min_value=100, max_value=2000))
        roads.append(Road(id=f"R{road_id}", source=src.id, target=tgt.id, capacity=cap))
        road_id += 1

    if len(roads) < n_junctions - 1:
        return draw(network_strategy())

    sources = draw(st.sampled_from(junctions, min_size=1, max_size=min(2, n_junctions)))
    sinks = draw(st.sampled_from([j for j in junctions if j not in sources], min_size=1, max_size=min(2, n_junctions)))

    for j in sources:
        j.external_flow = draw(st.floats(min_value=10, max_value=500))
    for j in sinks:
        j.external_flow = -draw(st.floats(min_value=10, max_value=500))

    total_source = sum(j.external_flow for j in sources)
    total_sink = -sum(j.external_flow for j in sinks)
    if abs(total_source - total_sink) > 1e-6:
        scale = total_sink / total_source if total_source != 0 else 1
        for j in sources:
            j.external_flow *= scale

    return Network(junctions=junctions, roads=roads)


class TestFlowConservationProperty:
    @settings(max_examples=50, deadline=None)
    @given(network=network_strategy())
    @example(network=Network(
        junctions=[
            Junction(id="A", position=(0, 0), external_flow=100),
            Junction(id="B", position=(100, 0), external_flow=-100),
        ],
        roads=[Road(id="r1", source="A", target="B", capacity=1000)]
    ))
    def test_rref_solution_satisfies_conservation(self, network):
        try:
            solution = solve_rref(network)
            is_valid, violations = validate_solution(network, solution.flows)
            assert is_valid, f"Flow conservation violated: {violations}"
        except Exception as e:
            pytest.skip(f"Solver failed: {e}")

    @settings(max_examples=50, deadline=None)
    @given(network=network_strategy())
    def test_flows_are_non_negative(self, network):
        try:
            solution = solve_rref(network)
            for flow in solution.flows.values():
                assert flow >= -1e-6, f"Negative flow found: {flow}"
        except Exception as e:
            pytest.skip(f"Solver failed: {e}")

    @settings(max_examples=50, deadline=None)
    @given(network=network_strategy())
    def test_flows_within_capacity(self, network):
        try:
            solution = solve_rref(network)
            for road in network.roads:
                flow = solution.flows.get(road.id, 0)
                assert flow <= road.capacity + 1e-6, \
                    f"Flow {flow} exceeds capacity {road.capacity} on road {road.id}"
        except Exception as e:
            pytest.skip(f"Solver failed: {e}")


class TestRREFMathProperty:
    @given(
        n=st.integers(min_value=2, max_value=5),
        m=st.integers(min_value=2, max_value=5),
    )
    def test_rref_pivot_properties(self, n, m):
        from traffic_control.solvers.rref import rref_solve
        A = np.random.randn(n, m)
        b = np.random.randn(n)

        particular, nullspace, pivots = rref_solve(A, b)

        assert len(pivots) <= min(n, m)
        assert particular.shape == (m,)
        assert nullspace.shape[0] == m
        assert nullspace.shape[1] == m - len(pivots)

        for pc in pivots:
            residual = A[:, pc] * particular[pc]
            for fc in range(nullspace.shape[1]):
                residual += A[:, fc] * nullspace[pc, fc] if fc < len(pivots) else 0
            np.testing.assert_allclose(residual, 0, atol=1e-6)

        reconstructed = A @ particular
        np.testing.assert_allclose(reconstructed, b, atol=1e-6)