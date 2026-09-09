import yaml
from typing import Dict, Any, List
from pydantic import BaseModel, Field

class AgentStep(BaseModel):
    state: str
    allowed_transitions: List[str]
    action: str

class AgentDSLSpec(BaseModel):
    agent_name: str
    version: str
    entry_state: str
    allowed_tools: List[str]
    max_token_budget: int
    steps: List[AgentStep]

class AgentDSLCompiler:
    def __init__(self):
        # Actions that require deep reasoning (Graph traversal, anomaly detection)
        self.high_complexity_actions = ["GRAPH_ORIGIN_TRACE", "ANOMALY_DETECTION", "TASKRABBIT_LTR_RANKING"]

    def compile_yaml_to_fsm(self, yaml_content: str) -> Dict[str, Any]:
        """Compiles declarative YAML into a validated FSM DAG execution structure."""
        parsed = yaml.safe_load(yaml_content)
        spec = AgentDSLSpec(**parsed['agent'])
        
        graph = {}
        for step in spec.steps:
            graph[step.state] = {
                "next_allowed": step.allowed_transitions,
                "action_type": step.action
            }
            
        return {
            "metadata": spec.model_dump(exclude={"steps"}),
            "compiled_dag": graph
        }

    def profile_complexity(self, compiled_fsm: Dict[str, Any]) -> int:
        """
        AST Complexity Profiler: Scores the DAG to determine if it needs 
        a heavy reasoning model (Claude) or a local SLM (Ollama 8B).
        """
        score = 0
        dag = compiled_fsm["compiled_dag"]
        
        # Base score on number of states
        score += len(dag) 
        
        # Add weight for complex actions
        for state, details in dag.items():
            if details["action_type"] in self.high_complexity_actions:
                score += 3
                
        # Add weight for number of tools required
        score += len(compiled_fsm["metadata"]["allowed_tools"])
        
        return score