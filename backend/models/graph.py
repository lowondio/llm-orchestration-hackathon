from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class NodeData(BaseModel):
    label: str
    model: Optional[str] = None
    systemPrompt: Optional[str] = None
    toolType: Optional[str] = None
    config: Optional[str] = None
    actionType: Optional[str] = None
    triggerType: Optional[str] = None
    cronExpression: Optional[str] = None
    interval: Optional[int] = None
    botToken: Optional[str] = None
    ragName: Optional[str] = None
    ragFiles: Optional[List[Dict[str, Any]]] = None
    chunkSize: Optional[int] = None
    chunkOverlap: Optional[int] = None
    topK: Optional[int] = None
    agentRole: Optional[str] = None
    agentModel: Optional[str] = None
    agentSystemPrompt: Optional[str] = None
    hitlMessage: Optional[str] = None
    hitlTimeout: Optional[int] = None

class Position(BaseModel):
    x: float
    y: float

class Node(BaseModel):
    id: str
    type: str
    position: Position
    data: NodeData

class Edge(BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: Optional[str] = None
    targetHandle: Optional[str] = None

class GraphSchema(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DeployResponse(BaseModel):
    status: str
    graph_id: str
    execution_order: List[str]
    message: str
