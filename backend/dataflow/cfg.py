from backend.dataflow.basicblock import BasicBlock
from queue import Queue
"""
CFG: Control Flow Graph

nodes: sequence of basicblock
edges: sequence of edge(u,v), which represents after block u is executed, block v may be executed
links: links[u][0] represent the Prev of u, links[u][1] represent the Succ of u,
"""


class CFG:
    def __init__(self, nodes: list[BasicBlock], edges: list[(int, int)]) -> None:
        self.nodes = nodes
        self.edges = edges
        self.reachable = set()
        self.links = []

        for i in range(len(nodes)):
            self.links.append((set(), set()))

        for (u, v) in edges:
            self.links[u][1].add(v)
            self.links[v][0].add(u)

        q = Queue()
        q.put(0)
        while q.qsize() > 0:
            current_node = q.get()
            self.reachable.add(current_node)
            unvisited_neighbors = self.links[current_node][1].difference(self.reachable)
            for neighbor in unvisited_neighbors:
                q.put(neighbor)

    def getBlock(self, id):
        return self.nodes[id]

    def getPrev(self, id):
        return self.links[id][0]

    def getSucc(self, id):
        return self.links[id][1]

    def getInDegree(self, id):
        return len(self.links[id][0])

    def getOutDegree(self, id):
        return len(self.links[id][1])

    def iterator(self): #iterate for DFS
        for n in self.reachable:
            yield self.nodes[n]

    def __len__(self):
        return len(self.reachable)

