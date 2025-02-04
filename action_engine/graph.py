from action_engine.types import Displayable


class Graph[N: Displayable, E]:
    """
    A directed graph with nodes of type N and edges of type E.
    """

    nodes: dict[N, list[N]]
    edges: dict[tuple[N, N], E]

    def __init__(self) -> None:
        self.nodes = {}
        self.edges = {}

    def add_node(self, node: N) -> None:
        """
        Add a node to the graph.
        """
        self.nodes[node] = []

    def add_edge(self, node1: N, node2: N, edge: E) -> None:
        """
        Add an edge between two nodes.
        """
        if node1 not in self.nodes:
            self.add_node(node1)
        if node2 not in self.nodes:
            self.add_node(node2)
        self.nodes[node1].append(node2)
        self.edges[(node1, node2)] = edge

    def get_edges(self, node: N) -> list[E]:
        """
        Get all edges originating from a node.
        """
        return [self.edges[(node, node2)] for node2 in self.nodes[node]]

    def get_nodes(self) -> list[N]:
        """
        Get all nodes in the graph.
        """
        return list(self.nodes.keys())

    def get_neighbors(self, node: N) -> list[N]:
        """
        Get all nodes connected to a given node.
        """
        return self.nodes[node]

    def display_mermaid(self) -> str:
        """
        Generates a Mermaid diagram string representing the graph.

        For example, the output might look like:

            graph TD
                A -- label1 --> B
                A --> C
                D

        Here:
          - "graph TD" specifies a top-down layout.
          - Each edge is defined using the syntax "Node1 -- label --> Node2".
          - If an edge has an empty label, it is omitted.
          - Isolated nodes (nodes without any edge) are also added.
        """
        # Start with a Mermaid graph declaration.
        mermaid = ["graph TD\n"]

        # Add edges with labels (if any)
        for node, neighbors in self.nodes.items():
            mermaid.append(
                f"{node.get_name()}({node.get_name()} \n +++++++++++++ \n {"+++++++++++++\n".join(node.get_info())})"
            )

        for coordinate, e in self.edges.items():
            mermaid.append(
                f"{coordinate[0].get_name()} -- {e} --> {coordinate[1].get_name()}"
            )

        return "\n".join(mermaid)

    def __str__(self) -> str:
        return f"Nodes: {self.nodes}\nEdges: {self.edges}"
