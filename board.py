from itertools import combinations
import math
"""Hex board geometry. Axial coordinates (q, r); s = -q - r is implied."""
 
Hex = tuple[int, int]
Vertex = tuple[Hex,Hex]
Edge = tuple[Hex,Hex]
Coordinates = tuple[int,int]
# Your six neighbour steps, in circular order: each step is itself a
# neighbour of the one before it, and the last wraps back to the first.
# Corner k of a hex is shared by the hex and its neighbours k and k+1 (mod 6).
DIRECTIONS: list[Hex] = [(1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1)]
 
 
class Board:
    def __init__(self, radius: int = 2):
        self.radius = radius
        self.hexes: list[Hex] = self._make_hexes()
        edge_set = set()
        vrtx_set = set()
        for h in self.hexes:
            edge_set.update(self.hex_edges(h))
            vrtx_set.update(self.hex_vertices(h))
        self.edges = edge_set
        self.vertices = vrtx_set
 
    def _make_hexes(self) -> list[Hex]:
        h = []
        for q in range(-self.radius,self.radius + 1):
            for r in range(-self.radius,self.radius + 1):
                s = -q -r
                if abs(s) <= self.radius and abs(r) <= self.radius and abs(q) <= self.radius:
                    h.append((q,r))
        return h
 
    def neighbors(self, h: Hex) -> list[Hex]:
        n = []
        q,r = h
        for i in DIRECTIONS:
            n.append((q + i[0], r + i[1]))
        return n

 
    def on_board(self, h: Hex) -> bool:
        for i in self.hexes:
            if h == i:
                return True
        return False 
    
    def hex_vertices(self, h: Hex) -> list[Vertex]:
        nbor = self.neighbors(h)
        vrtx_lst = []
        for i in range(6):
            n1 = nbor[i]
            n2 = nbor[(i + 1) % 6]
            hex_lst = [h,n1,n2]
            ht = tuple(sorted(hex_lst))
            vrtx_lst.append(ht)
        return vrtx_lst
        
    def hex_edges(self, h: Hex) -> list[Edge]:
        nbor = self.neighbors(h)
        edge = []
        for i in nbor:
            edge_lst = [h,i]
            ht = tuple(sorted(edge_lst))
            edge.append(ht)
        return edge

    def common_vertices(self,e:Edge) -> list[Vertex]:
        vrtx1 = self.hex_vertices(e[0])
        vrtx2 = self.hex_vertices(e[1])
        common_vrtx = []
        for vrtx in vrtx1:
            if vrtx in vrtx2:
                common_vrtx.append(vrtx)
        return common_vrtx
    
    def adjacent_edges(self,v:Vertex) -> list[Edge]:
        combos = combinations(v,2)
        adj = []
        for c in combos:
            if c in self.edges:
                adj.append(c)
        return adj
    
    def adjacent_vertices(self, v: Vertex) -> list[Vertex]:
        result = []
        for e in self.adjacent_edges(v):
            for end in self.common_vertex(e):
                if end != v:
                    result.append(end)
        return result
    
def coords_center(q,r,size) -> Coordinates:
    x = q * (math.sqrt(3) * size) + r * (math.sqrt(3) * size / 2) 
    y = r * (1.5 * size)
    return (x,y)

def corners_pix(q,r,size) -> list[Coordinates]:
    coords = []
    x, y = coords_center(q,r,size)
    for i in range(6):
        angle = (math.pi/180) * (60 * i - 30)
        corner = [x + size * math.cos(angle), y + size * math.sin(angle)]
        coords.append(corner)
    return coords

