# -*- coding: utf-8 -*-

import sma
from sma import MotifClassificator

class DiMotif11Classificator(MotifClassificator):
    """
    Classificator for directed motifs with signature (1, 1).
    """
    def __call__(self, motif):
        u, v = motif
        return 2 * self.G.has_edge(u, v) + self.G.has_edge(v, u)
    def info(self):
        return sma.DiMotif11Info

class DiMotif2Classificator(MotifClassificator):
    """
    Classificator for directed motifs with signature (2).
    """
    def __call__(self, motif):
        u, v = motif
        return self.G.has_edge(u, v) + self.G.has_edge(v, u)
    def info(self):
        return sma.DiMotif2Info

class DiMotif12Classificator(MotifClassificator):
    """
    Classificator for directed motifs with signature (1, 2).
    """
    def __call__(self, motif):
        a, b1, b2 = motif
        cl1 = "I" * (self.G.has_edge(b1, b2) + self.G.has_edge(b2, b1) + 1)
        cl2 = '.'.join(_classifyDi12Gadget(self.G, a, b1, b2))
        return '.'.join([cl1, cl2])
                      
    def info(self):
        return sma.DiMotif12Info

class DiMotif22Classificator(MotifClassificator):
    """
    Classificator for directed motifs with signature (1, 2).
    """
    def __call__(self, motif):
        a1, a2, b1, b2 = motif
        latin = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX']
        cl1 = latin[3 * (self.G.has_edge(b1, b2) + self.G.has_edge(b2, b1)) + \
                    (self.G.has_edge(a1, a2) + self.G.has_edge(a2, a1))]
        if self.G.has_edge(a1, a2) ^ self.G.has_edge(a2, a1):
            # asymmetry on top level
            # suppose a1 -> a2
            a1, a2 = _swapTailHead(self.G, a1, a2)
            if self.G.has_edge(b1, b2) ^ self.G.has_edge(b2, b1):
                # asymmetry on bottom level
                # suppose b1 -> b2
                b1, b2 = _swapTailHead(self.G, b1, b2)
                tr = {0 : 'n', 1 : 'd', 2 : 'u', 3 : 'b'}
                cl2 = ''.join(map(lambda x: tr[self.G.has_edge(*x) + 2*self.G.has_edge(*x[::-1])],
                                  [(a1, b1), (a1, b2), (a2, b1), (a2, b2)]))
            else:
                cl2 = _classifyDi22Gadget1Sym(self.G, a1, a2, b1, b2)
        else:
            if self.G.has_edge(b1, b2) ^ self.G.has_edge(b2, b1):
                # asymmetry on bottom level
                b1, b2 = _swapTailHead(self.G, b1, b2)
                cl2 = _classifyDi22Gadget1Sym(self.G, b1, b2, a1, a2)
            else:
                # symmetry on top and bottom level
                # split based on underlying undirected graph
                cl2a = _classify4Gadget(self.G.has_edge(a1, b1) or self.G.has_edge(b1, a1),
                                        self.G.has_edge(a1, b2) or self.G.has_edge(b2, a1),
                                        self.G.has_edge(a2, b1) or self.G.has_edge(b1, a2),
                                        self.G.has_edge(a2, b2) or self.G.has_edge(b2, a2))
                if cl2a == 'A':
                    cl2b = ''
                elif cl2a == 'B':
                    if self.G.has_edge(a1, b1) or self.G.has_edge(b1, a1):
                        cl2b = str(_classifyDi2Gadget(self.G, a1, b1))
                    elif self.G.has_edge(a1, b2) or self.G.has_edge(b2, a1):
                        cl2b = str(_classifyDi2Gadget(self.G, a1, b2))
                    elif self.G.has_edge(a2, b1) or self.G.has_edge(b1, a2):
                        cl2b = str(_classifyDi2Gadget(self.G, a2, b1))
                    elif self.G.has_edge(a2, b2) or self.G.has_edge(b2, a2):
                        cl2b = str(_classifyDi2Gadget(self.G, a2, b2))
                elif cl2a == 'C':
                    if ((self.G.has_edge(a1, b1) or self.G.has_edge(b1, a1)) and
                        self.G.has_edge(a2, b1) or self.G.has_edge(b1, a2)):
                        # rooted in b1
                        cl2b = _classifySymDi12Gadget(self.G, b1, a1, a2)[1]
                    else:
                        # rooted in b2
                        cl2b = _classifySymDi12Gadget(self.G, b2, a1, a2)[1]
                elif cl2a == 'D':
                    if ((self.G.has_edge(a1, b1) or self.G.has_edge(b1, a1)) and
                        self.G.has_edge(a1, b2) or self.G.has_edge(b2, a1)):
                        # rooted in a1
                        cl2b = _classifySymDi12Gadget(self.G, a1, b1, b2)[1]
                    else:
                        # rooted in a2
                        cl2b = _classifySymDi12Gadget(self.G, a2, b1, b2)[1]
                elif cl2a == 'E':
                    if ((self.G.has_edge(a1, b1) or self.G.has_edge(b1, a1)) and
                        self.G.has_edge(a2, b2) or self.G.has_edge(b2, a2)):
                        # parallels are a1-b1 and a2-b2
                        cl2b = str(_classifyDi22ParallelGadget(self.G, a1, a2, b1, b2))
                    else:
                        # parallels are a1-b2 and a2-b1
                        cl2b = str(_classifyDi22ParallelGadget(self.G, a1, a2, b2, b1))
                elif cl2a == 'F':
                    if not(self.G.has_edge(a1, b1) or self.G.has_edge(b1, a1)):
                        cl2b = str(_classifyDi3Path(self.G, a1, b2, a2, b1))
                    elif not(self.G.has_edge(a1, b2) or self.G.has_edge(b2, a1)):
                        cl2b = str(_classifyDi3Path(self.G, a1, b1, a2, b2))
                    elif not(self.G.has_edge(a2, b1) or self.G.has_edge(b1, a2)):
                        cl2b = str(_classifyDi3Path(self.G, a2, b2, a1, b1))
                    else:
                        cl2b = str(_classifyDi3Path(self.G, a2, b1, a1, b2))
                elif cl2a == 'G':
                    # complete underlying graph
                    cl2b = _classify4Gadget(self.G.has_edge(a1, b1) and self.G.has_edge(b1, a1),
                                            self.G.has_edge(a1, b2) and self.G.has_edge(b2, a1),
                                            self.G.has_edge(a2, b1) and self.G.has_edge(b1, a2),
                                            self.G.has_edge(a2, b2) and self.G.has_edge(b2, a2)).lower()
                    if cl2b == 'a': # nothing twice
                        cl2c = _classify4Gadget(self.G.has_edge(a1, b1),
                                                self.G.has_edge(a1, b2),
                                                self.G.has_edge(a2, b1),
                                                self.G.has_edge(a2, b2))
                    elif cl2b == 'b':
                        if self.G.has_edge(a1, b1) and self.G.has_edge(b1, a1):
                            cl2c = str(_classifyDi3Path(self.G, a1, b2, a2, b1))
                        elif self.G.has_edge(a1, b2) and self.G.has_edge(b2, a1):
                            cl2c = str(_classifyDi3Path(self.G, a1, b1, a2, b2))
                        elif self.G.has_edge(a2, b1) and self.G.has_edge(b1, a2):
                            cl2c = str(_classifyDi3Path(self.G, a2, b2, a1, b1))
                        else:
                            cl2c = str(_classifyDi3Path(self.G, a2, b1, a1, b2))
                    elif cl2b == 'c' or cl2b == 'd' or cl2b == 'e':
                        if self.G.has_edge(a1, b1) and self.G.has_edge(b1, a1):
                            if self.G.has_edge(a1, b2) and self.G.has_edge(b2, a1):
                                cl2c = str(_classifySymDi12Gadget(self.G, a2, b1, b2)[1])
                            elif self.G.has_edge(a2, b1) and self.G.has_edge(b1, a2):
                                cl2c = str(_classifySymDi12Gadget(self.G, b2, a1, a2)[1])
                            else: # parallel cross
                                cl2c = str(_classifyDi22ParallelGadget(self.G, a1, a2, b2, b1))
                        elif self.G.has_edge(a1, b2) and self.G.has_edge(b2, a1):
                            if self.G.has_edge(a2, b1) and self.G.has_edge(b1, a2):
                                cl2c = str(_classifyDi22ParallelGadget(self.G, a1, a2, b1, b2))
                            else:
                                cl2c = str(_classifySymDi12Gadget(self.G, b1, a1, a2)[1])
                        else:
                            cl2c = str(_classifySymDi12Gadget(self.G, a1, b1, b2)[1])
                    elif cl2b == 'f':
                        if not(self.G.has_edge(a1, b1) and self.G.has_edge(b1, a1)):
                            cl2c = str(_classifyDi2Gadget(self.G, a1, b1))
                        elif not(self.G.has_edge(a1, b2) and self.G.has_edge(b2, a1)):
                            cl2c = str(_classifyDi2Gadget(self.G, a1, b2))
                        elif not(self.G.has_edge(a2, b1) and self.G.has_edge(b1, a2)):
                            cl2c = str(_classifyDi2Gadget(self.G, a2, b1))
                        else:
                            cl2c = str(_classifyDi2Gadget(self.G, a2, b2))
                    else:
                        cl2c = ''
                    cl2a = ''.join([cl2a, cl2b])
                    cl2b = cl2c
                cl2 = '.'.join([cl2a, cl2b]) if cl2b != '' else cl2a
        return '.'.join([cl1, cl2])
            
                      
    def info(self):
        return sma.DiMotif22Info

# Helper function

def _swapTailHead(G, a, b):
    """
    Swaps two nodes such that the graph contains the directed edge a -> b.
    """
    if G.has_edge(a, b):
        return (a, b)
    else:
        return (b, a)

def _classifyDi12Gadget(G, a, b1, b2):
    """
    Classifies a directed graph consisting of one node a on the upper level and
    two nodes on the lower level (b1, b2). The distinct edge between (b1, b2) is
    not considered.
    """
    if G.has_edge(b1, b2) ^ G.has_edge(b2, b1):
        # asymmetrical
        # suppose x -> y
        x, y = _swapTailHead(G, b1, b2)
        int_code = sma.binaryArrayHornersMethod([G.has_edge(a, x),
                                                 G.has_edge(x, a),
                                                 G.has_edge(a, y),
                                                 G.has_edge(y, a)])
        if int_code == 0:
            return ('A',)
        elif int_code <= 4:
            return "B", str(int_code)
        elif int_code <= 7:
            return "C", str(int_code - 4)
        elif int_code == 8:
            return "B", "5"
        elif int_code <= 11:
            return "C", str(int_code - 5)
        elif int_code == 12:
            return "B", "6"
        else:
            return "C", str(int_code - 6)
    else:
        return _classifySymDi12Gadget(G, a, b1, b2)

def _classifySymDi12Gadget(G, a, b1, b2):
    if ((G.has_edge(a, b1) or G.has_edge(b1, a)) and
        (G.has_edge(a, b2) or G.has_edge(b2, a))):
        if (G.has_edge(a, b1) and G.has_edge(a, b2) and
            G.has_edge(b1, a) and G.has_edge(b2, a)):
            return "C", "6"
        elif ((G.has_edge(a, b1) and G.has_edge(b1, a) and G.has_edge(a, b2)) or
              (G.has_edge(a, b2) and G.has_edge(b2, a) and G.has_edge(a, b1))):
            return "C", "5"
        elif ((G.has_edge(a, b1) and G.has_edge(b1, a) and G.has_edge(b2, a)) or
              (G.has_edge(a, b2) and G.has_edge(b2, a) and G.has_edge(b1, a))):
            return "C", "4"
        elif G.has_edge(a, b1) and G.has_edge(a, b2):
            return "C", "3"
        elif G.has_edge(b1, a) and G.has_edge(b2, a):
            return "C", "1"
        else:
            return "C", "2"
    elif (G.has_edge(a, b1) or G.has_edge(b1, a) or
          G.has_edge(a, b2) or G.has_edge(b2, a)):
        if ((G.has_edge(a, b1) and G.has_edge(b1, a)) or
            (G.has_edge(a, b2) and G.has_edge(b2, a))):
            return "B", "3"
        elif G.has_edge(a, b1) or G.has_edge(a, b2):
            return "B", "2"
        else:
            return "B", "1"
    else:
        return ('A',)

def _classifyDi22Gadget1Sym(G, a, b, c1, c2):
    """
    Suppose a -> b
    """
    return ''.join(_classifyDi12Gadget(G, a, c1, c2) + \
                   _classifyDi12Gadget(G, b, c1, c2))
    
def _classifyDi22ParallelGadget(G, a1, a2, b1, b2):
    """
    Suppose a1 - b1, a2 - b2 and no other edges. What are the directions?
    
    Returns classes 1, …, 6.
    """
    x = G.has_edge(a1, b1) + 2 * G.has_edge(b1, a1)
    y = G.has_edge(a2, b2) + 2 * G.has_edge(b2, a2)
    z = 4 * y + x
    return {5 : 1, 6 : 2, 7 : 3, 9 : 2, 
            13 : 2, 10 : 4, 11 : 5, 14 : 5, 15 : 6}[z]

def _classify4Gadget(a1b1, a1b2, a2b1, a2b2):
    s = a1b1 + a1b2 + a2b1 + a2b2
    if s == 0:
        return 'A'
    elif s == 1:
        return 'B'
    elif s == 2:
        if (a1b1 and a2b1) or (a1b2 and a2b2):
            return 'C'
        elif (a1b1 and a1b2) or (a2b1 and a2b2):
            return 'D'
        else:
            return 'E'
    elif s == 3:
        return 'F'
    else:
        return 'G'

def _classifyDi2Gadget(G, a, b):
    return 2 * G.has_edge(a, b) + G.has_edge(b, a)

def _classifyDi3Path(G, a, b, c, d):
    """
    Suppose path a-b-c-d. What are the directions?
    
    Classes nnn, ..., bbb.
    """
    tr = {0 : 'n', 1 : 'd', 2 : 'u', 3 : 'b'}
    return ''.join(map(lambda x: tr[G.has_edge(*x) + 2*G.has_edge(*x[::-1])],
                       [(a, b), (b, c), (c, d)]))
