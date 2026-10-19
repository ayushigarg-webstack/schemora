"""
Diagram-Specific Layout Strategies.
Implements layered Sugiyama DAG, hierarchical tiered architecture,
force-directed spring for concept maps, timeline lifelines for sequence diagrams,
orthogonal grid for ER diagrams, cluster topology for networks, and strict DAG layouts.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict, deque
import math
import networkx as nx

from ir.models import DiagramGraph, DiagramNode, DiagramEdge, LayoutCoordinate, DiagramType
from .models import LayoutOptions, LayoutStrategy, BoundingBox, LayoutResult


class BaseLayoutStrategy(ABC):
    """Abstract base class for all layout strategies."""

    strategy: LayoutStrategy

    @abstractmethod
    def compute_layout(self, graph: DiagramGraph, options: LayoutOptions) -> Dict[str, LayoutCoordinate]:
        """Calculates coordinates for all nodes in the graph."""
        pass

    @classmethod
    def compute_bounding_box(
        cls,
        coords: Dict[str, LayoutCoordinate],
        options: LayoutOptions
    ) -> BoundingBox:
        """Calculates bounding box of laid-out nodes including dimensions."""
        if not coords:
            return BoundingBox(
                min_x=0.0,
                min_y=0.0,
                max_x=options.canvas_padding * 2,
                max_y=options.canvas_padding * 2
            )

        min_x = min(c.x for c in coords.values())
        min_y = min(c.y for c in coords.values())
        max_x = max(c.x + (c.width or options.node_width) for c in coords.values())
        max_y = max(c.y + (c.height or options.node_height) for c in coords.values())

        return BoundingBox(
            min_x=min_x,
            min_y=min_y,
            max_x=max_x,
            max_y=max_y,
        )

    @classmethod
    def layout_disconnected_components(
        cls,
        graph: DiagramGraph,
        component_nodes: List[List[str]],
        options: LayoutOptions,
        sub_layout_fn
    ) -> Dict[str, LayoutCoordinate]:
        """
        Lays out multiple disconnected components side-by-side or in a 2D tile
        to prevent overlapping.
        """
        all_coords: Dict[str, LayoutCoordinate] = {}
        current_x_offset = options.canvas_padding
        current_y_offset = options.canvas_padding
        max_height_in_row = 0.0

        for comp in component_nodes:
            sub_nodes = [n for n in graph.nodes if n.id in comp]
            sub_node_ids = set(comp)
            sub_edges = [e for e in graph.edges if e.source in sub_node_ids and e.target in sub_node_ids]

            sub_graph = DiagramGraph(
                id=f"{graph.id or 'graph'}_sub",
                diagram_type=graph.diagram_type,
                version=graph.version,
                nodes=sub_nodes,
                edges=sub_edges,
                metadata=graph.metadata,
            )

            # Compute relative coordinates for this component
            sub_coords = sub_layout_fn(sub_graph, options)
            bbox = cls.compute_bounding_box(sub_coords, options)

            # Translate sub_coords by current offset
            for nid, coord in sub_coords.items():
                rel_x = coord.x - bbox.min_x
                rel_y = coord.y - bbox.min_y
                all_coords[nid] = LayoutCoordinate(
                    x=round(current_x_offset + rel_x, 2),
                    y=round(current_y_offset + rel_y, 2),
                    width=coord.width,
                    height=coord.height,
                    rank=coord.rank,
                )

            comp_w = bbox.width
            comp_h = bbox.height
            max_height_in_row = max(max_height_in_row, comp_h)

            current_x_offset += comp_w + options.component_margin

            # Wrap row if row gets too wide (> 1800px)
            if current_x_offset > 1800.0:
                current_x_offset = options.canvas_padding
                current_y_offset += max_height_in_row + options.component_margin
                max_height_in_row = 0.0

        return all_coords


class FlowchartLayoutStrategy(BaseLayoutStrategy):
    """
    Layered Sugiyama DAG layout for flowcharts.
    Handles cycles by reversing back-edges during topological ranking.
    Spreads decision branches horizontally to avoid label/node collisions.
    """

    strategy = LayoutStrategy.LAYERED_SUGIYAMA

    def compute_layout(self, graph: DiagramGraph, options: LayoutOptions) -> Dict[str, LayoutCoordinate]:
        if not graph.nodes:
            return {}

        node_ids = {n.id for n in graph.nodes}
        if len(node_ids) == 1:
            nid = next(iter(node_ids))
            return {
                nid: LayoutCoordinate(
                    x=options.canvas_padding,
                    y=options.canvas_padding,
                    width=options.node_width,
                    height=options.node_height,
                    rank=0,
                )
            }

        # Step 1: Detect weakly connected components
        G_full = nx.DiGraph()
        for nid in node_ids:
            G_full.add_node(nid)
        for e in graph.edges:
            if e.source in node_ids and e.target in node_ids:
                G_full.add_edge(e.source, e.target)

        components = [sorted(list(c)) for c in nx.weakly_connected_components(G_full)]
        if len(components) > 1:
            return self.layout_disconnected_components(
                graph, components, options, self._layout_single_component
            )

        return self._layout_single_component(graph, options)

    def _layout_single_component(self, graph: DiagramGraph, options: LayoutOptions) -> Dict[str, LayoutCoordinate]:
        G = nx.DiGraph()
        node_map = {n.id: n for n in graph.nodes}
        for n in graph.nodes:
            G.add_node(n.id)
        for e in graph.edges:
            if e.source in node_map and e.target in node_map:
                G.add_edge(e.source, e.target)

        # Step 2: Handle cycles by identifying back-edges via DFS
        dag = G.copy()
        try:
            cycles = list(nx.simple_cycles(dag))
            for cycle in cycles:
                # Find the back-edge closing the cycle and remove from DAG ranking
                for i in range(len(cycle)):
                    u = cycle[i]
                    v = cycle[(i + 1) % len(cycle)]
                    if dag.has_edge(u, v):
                        dag.remove_edge(u, v)
                        break
        except Exception:
            pass

        # Step 3: Assign topological ranks
        ranks: Dict[str, int] = {}
        in_degrees = dict(dag.in_degree())
        roots = [n for n, d in in_degrees.items() if d == 0]
        if not roots:
            roots = [sorted(list(dag.nodes))[0]]

        queue = deque([(r, 0) for r in roots])
        visited: Set[str] = set()

        for r in roots:
            ranks[r] = 0

        while queue:
            curr, rk = queue.popleft()
            for succ in dag.successors(curr):
                new_rk = rk + 1
                if succ not in ranks or new_rk > ranks[succ]:
                    ranks[succ] = new_rk
                if succ not in visited:
                    visited.add(succ)
                    queue.append((succ, new_rk))

        # Ensure all nodes have a rank
        for nid in G.nodes:
            if nid not in ranks:
                ranks[nid] = 0

        # Step 4: Group nodes by rank
        rank_groups: Dict[int, List[str]] = defaultdict(list)
        for nid, rk in ranks.items():
            rank_groups[rk].append(nid)

        sorted_ranks = sorted(rank_groups.keys())

        # Step 5: Order nodes within ranks to reduce crossings (barycentric heuristic)
        for rk in sorted_ranks:
            group = rank_groups[rk]
            if rk == 0:
                group.sort()
            else:
                # Sort by average position of parents in previous ranks
                def parent_pos_avg(n_id: str) -> float:
                    preds = [p for p in G.predecessors(n_id) if ranks.get(p, 0) < rk]
                    if not preds:
                        return 0.0
                    return sum(rank_groups[ranks[p]].index(p) for p in preds if p in rank_groups[ranks[p]]) / len(preds)

                group.sort(key=parent_pos_avg)

        # Step 6: Coordinate assignment
        # Calculate maximum width required by any rank
        max_nodes_in_rank = max(len(g) for g in rank_groups.values()) if rank_groups else 1
        x_gap = options.x_spacing
        y_gap = options.y_spacing
        w = options.node_width
        h = options.node_height

        total_canvas_width = max(
            800.0,
            max_nodes_in_rank * (w + x_gap) + options.canvas_padding * 2
        )

        coords: Dict[str, LayoutCoordinate] = {}

        for rk in sorted_ranks:
            group = rank_groups[rk]
            rank_node_count = len(group)
            rank_width = rank_node_count * w + (rank_node_count - 1) * x_gap
            # Center this rank horizontally
            start_x = (total_canvas_width - rank_width) / 2.0
            y_pos = options.canvas_padding + rk * (h + y_gap)

            for i, nid in enumerate(group):
                x_pos = start_x + i * (w + x_gap)
                node_obj = node_map.get(nid)
                # Diamond / decision nodes slightly larger for readable branches
                is_decision = node_obj and node_obj.type.lower() in {"decision", "condition", "branch"}
                nw = w * 1.1 if is_decision else w
                nh = h * 1.1 if is_decision else h

                if options.direction == "LR":
                    # Swap X and Y for Left-to-Right layout
                    coords[nid] = LayoutCoordinate(
                        x=round(y_pos, 2),
                        y=round(x_pos, 2),
                        width=nw,
                        height=nh,
                        rank=rk,
                    )
                else:
                    coords[nid] = LayoutCoordinate(
                        x=round(x_pos, 2),
                        y=round(y_pos, 2),
                        width=nw,
                        height=nh,
                        rank=rk,
                    )

        return coords


class ArchitectureLayoutStrategy(BaseLayoutStrategy):
    """
    Hierarchical tiered layout for software architecture.
    Partitions nodes into architectural layers:
    Tier 0: Clients / User Interface / CDN
    Tier 1: Ingress / API Gateway / Load Balancer
    Tier 2: Application Services / Microservices / Workers
    Tier 3: Messaging / Event Bus / Kafka / Queues
    Tier 4: Databases / Caches / Storage
    Tier 5: External Services / Third-Party APIs
    """

    strategy = LayoutStrategy.HIERARCHICAL_TIERED

    TIER_KEYWORDS = {
        0: ["client", "user", "browser", "mobile", "frontend", "ui", "react", "vue", "angular", "ios", "android"],
        1: ["gateway", "load_balancer", "proxy", "nginx", "envoy", "traefik", "ingress", "api_gateway", "cdn"],
        2: ["service", "api", "backend", "microservice", "worker", "app", "auth", "payment", "order", "server"],
        3: ["queue", "kafka", "rabbitmq", "event_bus", "pubsub", "sqs", "sns", "broker"],
        4: ["database", "db", "cache", "redis", "postgres", "mysql", "mongodb", "storage", "s3", "blob", "datastore"],
        5: ["external", "third_party", "stripe", "twilio", "aws", "gcp", "azure"],
    }

    def compute_layout(self, graph: DiagramGraph, options: LayoutOptions) -> Dict[str, LayoutCoordinate]:
        if not graph.nodes:
            return {}

        node_map = {n.id: n for n in graph.nodes}
        tier_assignments: Dict[str, int] = {}

        # Classify each node into a tier
        for nid, node in node_map.items():
            assigned_tier = None
            text_to_check = f"{node.type} {node.label} {nid}".lower()

            for tier_idx, keywords in self.TIER_KEYWORDS.items():
                if any(kw in text_to_check for kw in keywords):
                    assigned_tier = tier_idx
                    break

            if assigned_tier is None:
                # Infer tier from topological in/out degree
                in_deg = len([e for e in graph.edges if e.target == nid])
                out_deg = len([e for e in graph.edges if e.source == nid])
                if in_deg == 0:
                    assigned_tier = 0  # Ingress/Source
                elif out_deg == 0:
                    assigned_tier = 4  # Sink/Storage
                else:
                    assigned_tier = 2  # Intermediate Service

            tier_assignments[nid] = assigned_tier

        # Group by tier
        tier_groups: Dict[int, List[str]] = defaultdict(list)
        for nid, tier in tier_assignments.items():
            tier_groups[tier].append(nid)

        sorted_tiers = sorted(tier_groups.keys())
        w = options.node_width * 1.1
        h = options.node_height
        x_gap = options.x_spacing * 1.2
        y_gap = options.y_spacing * 1.4

        max_nodes = max(len(g) for g in tier_groups.values()) if tier_groups else 1
        canvas_width = max(900.0, max_nodes * (w + x_gap) + options.canvas_padding * 2)

        coords: Dict[str, LayoutCoordinate] = {}

        for tier_idx, tier in enumerate(sorted_tiers):
            group = sorted(tier_groups[tier])
            count = len(group)
            tier_width = count * w + (count - 1) * x_gap
            start_x = (canvas_width - tier_width) / 2.0
            y_pos = options.canvas_padding + tier_idx * (h + y_gap)

            for i, nid in enumerate(group):
                x_pos = start_x + i * (w + x_gap)
                coords[nid] = LayoutCoordinate(
                    x=round(x_pos, 2),
                    y=round(y_pos, 2),
                    width=w,
                    height=h,
                    rank=tier,
                )

        return coords


class ConceptMapLayoutStrategy(BaseLayoutStrategy):
    """
    Force-directed spring layout for Concept Maps.
    Uses NetworkX spring_layout (Fruchterman-Reingold) with deterministic seed,
    rescaled to canvas dimensions with collision avoidance.
    """

    strategy = LayoutStrategy.FORCE_DIRECTED

    def compute_layout(self, graph: DiagramGraph, options: LayoutOptions) -> Dict[str, LayoutCoordinate]:
        if not graph.nodes:
            return {}

        n_nodes = len(graph.nodes)
        node_ids = sorted([n.id for n in graph.nodes])

        if n_nodes == 1:
            return {
                node_ids[0]: LayoutCoordinate(
                    x=options.canvas_padding,
                    y=options.canvas_padding,
                    width=options.node_width,
                    height=options.node_height,
                    rank=0,
                )
            }

        # Build undirected graph for force physics
        G = nx.Graph()
        for nid in node_ids:
            G.add_node(nid)
        for e in graph.edges:
            if e.source in node_ids and e.target in node_ids:
                G.add_edge(e.source, e.target)

        # NetworkX Fruchterman-Reingold layout
        k_dist = max(1.0, 3.0 / math.sqrt(n_nodes))
        pos = nx.spring_layout(G, k=k_dist, iterations=100, seed=options.seed)

        # Canvas bounding scale
        canvas_w = max(900.0, n_nodes * 130.0)
        canvas_h = max(700.0, n_nodes * 100.0)
        padding = options.canvas_padding * 1.5

        coords: Dict[str, LayoutCoordinate] = {}
        for nid, (nx_x, nx_y) in pos.items():
            # nx coords are in range [-1.0, 1.0]
            screen_x = padding + ((nx_x + 1.0) / 2.0) * (canvas_w - padding * 2)
            screen_y = padding + ((nx_y + 1.0) / 2.0) * (canvas_h - padding * 2)
            coords[nid] = LayoutCoordinate(
                x=round(screen_x, 2),
                y=round(screen_y, 2),
                width=options.node_width,
                height=options.node_height,
                rank=None,
            )

        # Collision avoidance pass: separate overlapping bounding boxes
        w = options.node_width + 30.0
        h = options.node_height + 25.0
        coords_list = list(coords.keys())

        for _ in range(5):  # 5 relaxation passes
            overlaps_found = False
            for i in range(len(coords_list)):
                for j in range(i + 1, len(coords_list)):
                    n1 = coords_list[i]
                    n2 = coords_list[j]
                    c1 = coords[n1]
                    c2 = coords[n2]

                    dx = c2.x - c1.x
                    dy = c2.y - c1.y
                    dist_x = abs(dx)
                    dist_y = abs(dy)

                    if dist_x < w and dist_y < h:
                        overlaps_found = True
                        push_x = (w - dist_x) / 2.0 * (1.0 if dx >= 0 else -1.0)
                        push_y = (h - dist_y) / 2.0 * (1.0 if dy >= 0 else -1.0)
                        c1.x = max(padding, round(c1.x - push_x, 2))
                        c1.y = max(padding, round(c1.y - push_y, 2))
                        c2.x = max(padding, round(c2.x + push_x, 2))
                        c2.y = max(padding, round(c2.y + push_y, 2))
            if not overlaps_found:
                break

        return coords


class SequenceDiagramLayoutStrategy(BaseLayoutStrategy):
    """
    Timeline Lifeline layout for Sequence Diagrams.
    Participants arranged along horizontal X axis at top with uniform spacing.
    Lifelines extend downwards.
    Messages (edges) descend monotonically on Y axis by sequence_order.
    """

    strategy = LayoutStrategy.TIMELINE_LIFELINE

    def compute_layout(self, graph: DiagramGraph, options: LayoutOptions) -> Dict[str, LayoutCoordinate]:
        if not graph.nodes:
            return {}

        node_ids = sorted([n.id for n in graph.nodes])
        # Order participants by appearance order in edges if available
        participant_order: List[str] = []
        for e in sorted(graph.edges, key=lambda x: x.sequence_order or 0):
            if e.source in node_ids and e.source not in participant_order:
                participant_order.append(e.source)
            if e.target in node_ids and e.target not in participant_order:
                participant_order.append(e.target)

        for nid in node_ids:
            if nid not in participant_order:
                participant_order.append(nid)

        w = options.node_width
        x_gap = options.x_spacing * 1.5
        lifeline_length = max(400.0, (len(graph.edges) + 2) * 70.0)

        coords: Dict[str, LayoutCoordinate] = {}
        for idx, pid in enumerate(participant_order):
            x_pos = options.canvas_padding + idx * (w + x_gap)
            coords[pid] = LayoutCoordinate(
                x=round(x_pos, 2),
                y=options.canvas_padding,
                width=w,
                height=lifeline_length,
                rank=idx,
            )

        return coords


class ERDiagramLayoutStrategy(BaseLayoutStrategy):
    """
    Orthogonal grid layout for Entity-Relationship (ER) diagrams.
    Places entity tables in structured rows and columns,
    minimizing edge crossings by placing connected tables in neighboring cells.
    """

    strategy = LayoutStrategy.ORTHOGONAL_GRID

    def compute_layout(self, graph: DiagramGraph, options: LayoutOptions) -> Dict[str, LayoutCoordinate]:
        if not graph.nodes:
            return {}

        node_ids = sorted([n.id for n in graph.nodes])
        n_nodes = len(node_ids)

        # Determine grid dimensions: 2 columns for <= 6 nodes, 3 columns for <= 12, etc.
        cols = 2 if n_nodes <= 6 else (3 if n_nodes <= 15 else 4)

        # Sort entities by degree (most connected placed centrally)
        degree_map: Dict[str, int] = defaultdict(int)
        for e in graph.edges:
            degree_map[e.source] += 1
            degree_map[e.target] += 1

        sorted_nodes = sorted(node_ids, key=lambda x: -degree_map[x])

        w = options.node_width * 1.2
        h = options.node_height * 1.5
        x_gap = options.x_spacing * 1.5
        y_gap = options.y_spacing * 1.2

        coords: Dict[str, LayoutCoordinate] = {}
        for idx, nid in enumerate(sorted_nodes):
            row = idx // cols
            col = idx % cols
            x_pos = options.canvas_padding + col * (w + x_gap)
            y_pos = options.canvas_padding + row * (h + y_gap)

            coords[nid] = LayoutCoordinate(
                x=round(x_pos, 2),
                y=round(y_pos, 2),
                width=w,
                height=h,
                rank=row,
            )

        return coords


class NetworkTopologyLayoutStrategy(BaseLayoutStrategy):
    """
    Cluster / Hub-and-Spoke layout for Network Topologies.
    Identifies core routing hubs and positions peripherals in radial rings.
    """

    strategy = LayoutStrategy.CLUSTER_TOPOLOGY

    def compute_layout(self, graph: DiagramGraph, options: LayoutOptions) -> Dict[str, LayoutCoordinate]:
        if not graph.nodes:
            return {}

        node_map = {n.id: n for n in graph.nodes}
        node_ids = sorted([n.id for n in graph.nodes])

        if len(node_ids) == 1:
            return {
                node_ids[0]: LayoutCoordinate(
                    x=options.canvas_padding,
                    y=options.canvas_padding,
                    width=options.node_width,
                    height=options.node_height,
                    rank=0,
                )
            }

        # Identify hubs: router, switch, gateway, firewall, or highest degree
        hub_keywords = {"router", "switch", "gateway", "firewall", "core", "hub"}
        hubs: List[str] = []
        for nid, node in node_map.items():
            if any(kw in f"{node.type} {node.label} {nid}".lower() for kw in hub_keywords):
                hubs.append(nid)

        if not hubs:
            # Fallback to node with max degree
            degree_map: Dict[str, int] = defaultdict(int)
            for e in graph.edges:
                degree_map[e.source] += 1
                degree_map[e.target] += 1
            max_deg_node = max(node_ids, key=lambda x: degree_map[x])
            hubs = [max_deg_node]

        primary_hub = hubs[0]
        peripherals = [nid for nid in node_ids if nid != primary_hub]

        center_x = 500.0
        center_y = 400.0
        radius = max(200.0, len(peripherals) * 35.0)

        coords: Dict[str, LayoutCoordinate] = {}
        coords[primary_hub] = LayoutCoordinate(
            x=center_x,
            y=center_y,
            width=options.node_width * 1.1,
            height=options.node_height * 1.1,
            rank=0,
        )

        n_periph = len(peripherals)
        for idx, pid in enumerate(peripherals):
            angle = (2.0 * math.pi * idx) / max(1, n_periph)
            px = center_x + radius * math.cos(angle)
            py = center_y + radius * math.sin(angle)
            coords[pid] = LayoutCoordinate(
                x=round(px, 2),
                y=round(py, 2),
                width=options.node_width,
                height=options.node_height,
                rank=1,
            )

        return coords


class DependencyGraphLayoutStrategy(BaseLayoutStrategy):
    """
    Strict DAG layout for task workflows and package dependency graphs.
    Enforces strict topological tier ordering from bottom-up or top-down.
    """

    strategy = LayoutStrategy.STRICT_DAG

    def compute_layout(self, graph: DiagramGraph, options: LayoutOptions) -> Dict[str, LayoutCoordinate]:
        # Delegates to FlowchartLayoutStrategy with strict DAG parameters
        flow_strat = FlowchartLayoutStrategy()
        return flow_strat.compute_layout(graph, options)
