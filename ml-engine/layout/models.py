"""
Data models and configuration for diagram layout engines.
"""

from enum import Enum
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel, Field

from ir.models import LayoutCoordinate


class LayoutStrategy(str, Enum):
    """Supported layout algorithms."""
    LAYERED_SUGIYAMA = "layered_sugiyama"
    HIERARCHICAL_TIERED = "hierarchical_tiered"
    FORCE_DIRECTED = "force_directed"
    ORTHOGONAL_GRID = "orthogonal_grid"
    TIMELINE_LIFELINE = "timeline_lifeline"
    CLUSTER_TOPOLOGY = "cluster_topology"
    STRICT_DAG = "strict_dag"


class LayoutOptions(BaseModel):
    """Configurable options for layout geometry and spacing."""
    node_width: float = 160.0
    node_height: float = 60.0
    x_spacing: float = 80.0
    y_spacing: float = 100.0
    direction: str = "TB"  # "TB" (Top-to-Bottom) or "LR" (Left-to-Right)
    canvas_padding: float = 60.0
    seed: int = 42
    component_margin: float = 120.0


class BoundingBox(BaseModel):
    """Bounding dimensions of a laid-out graph or component."""
    min_x: float = 0.0
    min_y: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0

    @property
    def width(self) -> float:
        return max(0.0, self.max_x - self.min_x)

    @property
    def height(self) -> float:
        return max(0.0, self.max_y - self.min_y)


class LayoutResult(BaseModel):
    """Output summary of layout computation."""
    strategy: LayoutStrategy
    node_coordinates: Dict[str, LayoutCoordinate] = Field(default_factory=dict)
    bounding_box: BoundingBox = Field(default_factory=BoundingBox)
    canvas_width: float = 0.0
    canvas_height: float = 0.0
