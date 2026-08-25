use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Junction {
    pub id: String,
    pub position: [f64; 2],
    #[serde(rename = "junctionType")]
    pub junction_type: JunctionType,
    #[serde(rename = "externalFlow")]
    pub external_flow: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum JunctionType {
    Normal,
    Source,
    Sink,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Road {
    pub id: String,
    pub source: String,
    pub target: String,
    pub capacity: f64,
    pub length: f64,
    pub flow: f64,
    #[serde(rename = "costPerUnit")]
    pub cost_per_unit: f64,
    #[serde(rename = "freeFlowSpeed")]
    pub free_flow_speed: f64,
    pub lanes: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Network {
    pub junctions: Vec<Junction>,
    pub roads: Vec<Road>,
    pub metadata: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum SolverMethod {
    Rref,
    Simplex,
    MaxFlow,
    Dinic,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum OptimizationObjective {
    MinCost,
    MaxThroughput,
    MinTravelTime,
    BalanceLoad,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FlowSolution {
    pub flows: HashMap<String, f64>,
    pub method: SolverMethod,
    pub objective: Option<OptimizationObjective>,
    #[serde(rename = "objectiveValue")]
    pub objective_value: Option<f64>,
    #[serde(rename = "isFeasible")]
    pub is_feasible: bool,
    pub violations: Vec<String>,
    pub metadata: HashMap<String, serde_json::Value>,
}

impl FlowSolution {
    pub fn total_flow(&self) -> f64 {
        self.flows.values().sum()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SolveRequest {
    pub network: Network,
    pub method: SolverMethod,
    pub objective: Option<OptimizationObjective>,
    pub parameters: HashMap<String, serde_json::Value>,
}

impl Network {
    pub fn junction_ids(&self) -> Vec<&str> {
        self.junctions.iter().map(|j| j.id.as_str()).collect()
    }

    pub fn road_ids(&self) -> Vec<&str> {
        self.roads.iter().map(|r| r.id.as_str()).collect()
    }

    pub fn validate(&self) -> Result<(), String> {
        let junction_ids: std::collections::HashSet<_> = self.junctions.iter().map(|j| &j.id).collect();

        for road in &self.roads {
            if !junction_ids.contains(&road.source) {
                return Err(format!("Road {}: source junction '{}' not found", road.id, road.source));
            }
            if !junction_ids.contains(&road.target) {
                return Err(format!("Road {}: target junction '{}' not found", road.id, road.target));
            }
            if road.source == road.target {
                return Err(format!("Road {}: source and target cannot be the same", road.id));
            }
        }
        Ok(())
    }
}