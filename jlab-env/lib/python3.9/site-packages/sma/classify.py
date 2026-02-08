#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sma
import networkx as nx

class MotifClassificator:
    """
    Abstract super class of all motif classificators. Roughly speaking, a classificator
    maps a motif to its motif class, e.g. (Peter, Lake, Forrest) to 'I.C'.
    
    This class cannot be used as classificator as it is abstract. Use one of its
    inheritors, e.g. :py:class:`sma.FourMotifClassificator`.
    
    Each instance of this class is callable mapping a motif to its class. For
    constructing such an object a SEN must be provided. The syntax is as follows,
    cf. :py:class:`sma.ThreeMotifClassificator`.
    
    .. code-block :: Python
    
        import sma    
        # Let G be some SEN
        motif = ('Peter', 'Lake', 'Forrest')
        classificator = sma.ThreeMotifClassificator(G)
        clss = classificator(motif) # e.g. 'I.C'
    
    Each inheritor of this class must provide the following attributes. Note, that
    the values listed here are dummies. See the inheriting classes.
    """
    def __init__(self, G : nx.Graph):
        self.G = G
    def __call__(self, motif):
        raise NotImplementedError("sma.MotifClassificator is an abstract class which should not be used as MotifClassificator")
    def info(self):
        """
        Returns the motif database entry for the motifs classified by this classificator,
        i.e. a subclass of :py:class:`sma.MotifInfo`.
        """
        raise NotImplementedError("sma.MotifClassificator is an abstract class which should not be used as MotifClassificator")

def classify4Motif(G : nx.Graph, motif) -> str:
    """
    Classifies a 4-motif given as a 4-tuple of its nodes.
    
    See :py:meth:`sma.binaryCodeToClass4Motifs`.
    
    :param G: the graph
    :param motif: the motif given as 4-tuple of its nodes
    :returns: class of the motif as string, e.g. 'I.C'
    """
    s1,s2,e1,e2 = motif
    binary = sma.binaryArrayHornersMethod([
            G.has_edge(s1, s2),
            G.has_edge(s2, e2),
            G.has_edge(e1, e2),
            G.has_edge(s1, e1),
            G.has_edge(s1, e2),
            G.has_edge(s2, e1)
        ])
    return sma.binaryCodeToClass4Motifs(binary)

class FourMotifClassificator(MotifClassificator):
    """
    :py:class:`sma.MotifClassificator` for classifying 4-motifs. Wrapps
    :py:meth:`sma.classify4Motif`.
    """
    def __call__(self, motif):
        return classify4Motif(self.G, motif)
    def info(self):
        return sma.Motif4Info

def classify3Motif(G : nx.Graph, motif) -> str:
    """
    Classifies a 3-motif given as a 3-tuple of its nodes.
    
    See :py:meth:`sma.binaryCodeToClass3Motifs`.
    
    :param G: the graph
    :param motif: the motif given as 3-tuple of its nodes
    :returns: class of the motif as string, e.g. 'I.C'
    """
    a, b1, b2 = motif
    binary = sma.binaryArrayHornersMethod([
            G.has_edge(b1,b2),
            G.has_edge(a, b1),
            G.has_edge(a, b2)
            ])
    return sma.binaryCodeToClass3Motifs(binary)

class ThreeMotifClassificator(MotifClassificator):
    """
    :py:class:`sma.MotifClassificator` for classifying 3-motifs such as 3E- or
    3S-motifs. Wrapps :py:meth:`sma.classify3Motif`. See also 
    :py:class:`sma.ThreePMotifClassificator` for plain motifs.
    """
    def __call__(self, motif):
        return classify3Motif(self.G, motif)
    def info(self):
        return sma.Motif3Info


def classify2Motif(G : nx.Graph, motif) -> bool:
    """
    Classifies 2-motifs. These motifs consist of two vertices. Two classes of
    motifs occur. Either the two vertices are linked (type 1) or the two vertices 
    not linked (type 0).
    
    :param G: the SEN
    :param motif: a pair of two vertices, the motif
    """
    return int(G.has_edge(*motif))

class TwoMotifClassificator(MotifClassificator):
    """
    :py:class:`sma.MotifClassificator` for classifying 2-motifs. See 
    :py:meth:`sma.classify2Motif`.
    """
    def __call__(self, motif):
        return classify2Motif(self.G, motif)
    def info(self):
        return sma.Motif2Info

    
def classify3pMotif(G : nx.Graph, motif) -> int:
    """
    Classifies a plain 3-motif given as a 3-tuple of its nodes.
    
    Since the three vertices in the motif are not distinguishable, there exist 
    four classes of motifs:
        
        - type 0: no edges
        - type 1: one edge
        - type 2: two edges
        - type 3: three edges
    
    :param G: the graph
    :param motif: the motif given as 3-tuple of its nodes
    :returns: class of the motif as integer
    """
    return (G.has_edge(motif[0], motif[1]) 
            + G.has_edge(motif[1], motif[2])
            + G.has_edge(motif[2], motif[0]))
    
class ThreePMotifClassificator(MotifClassificator):
    """
    :py:class:`sma.MotifClassificator` for classifying plain 3-motifs. These are
    motifs that do not respect whether the individual nodes are social or ecological.
    
    See :py:class:`sma.ThreeMotifClassificator` for the classificator that respects
    the types of the nodes.
    """
    def __call__(self, motif):
        return classify3pMotif(self.G, motif)
    def info(self):
        return sma.Motif3pInfo

class OneMotifClassificator(MotifClassificator):
    """
    :py:class:`sma.MotifClassificator` for classifying 1-motifs. Such motifs
    consist only of a single vertex. 
    """
    def __call__(self, motif):
        return 1
    def info(self):
        return sma.Motif1Info
    
class TwoThreeMotifClassificator(MotifClassificator):
    """
    :py:class:`sma.MotifClassificator` for classifying (2,3)-motifs.
    """
    def __call__(self, motif):
        return classify23Motif(self.G, motif)
    def info(self):
        return sma.Motif23Info
    
def classify23Motif(G : nx.Graph, motif) -> int:
    a1, a2, b1, b2, b3 = motif
    if not G.has_edge(a1, a2):
        return -1
    if G.has_edge(b1, b2) and G.has_edge(b2, b3):
        p1, p2, p3 = b1, b2, b3
        if G.has_edge(p1, p3) or G.has_edge(a1, p2) or G.has_edge(a2, p2):
            return -1
        if ((G.has_edge(a1, p1) and G.has_edge(a2, p3) and
             not(G.has_edge(a1, p3)) and not(G.has_edge(a2, p1))) or
            (G.has_edge(a2, p1) and G.has_edge(a1, p3) and
             not(G.has_edge(a2, p3)) and not(G.has_edge(a1, p1)))):
             return 1
        return -1
    elif G.has_edge(b1, b3) and G.has_edge(b3, b2):
        p1, p2, p3 = b1, b3, b2
        if G.has_edge(p1, p3) or G.has_edge(a1, p2) or G.has_edge(a2, p2):
            return -1
        if ((G.has_edge(a1, p1) and G.has_edge(a2, p3) and
             not(G.has_edge(a1, p3)) and not(G.has_edge(a2, p1))) or
            (G.has_edge(a2, p1) and G.has_edge(a1, p3) and
             not(G.has_edge(a2, p3)) and not(G.has_edge(a1, p1)))):
             return 1
        return -1
    elif G.has_edge(b2, b1) and G.has_edge(b1, b3):
        p1, p2, p3 = b2, b1, b3
        if G.has_edge(p1, p3) or G.has_edge(a1, p2) or G.has_edge(a2, p2):
            return -1
        if ((G.has_edge(a1, p1) and G.has_edge(a2, p3) and
             not(G.has_edge(a1, p3)) and not(G.has_edge(a2, p1))) or
            (G.has_edge(a2, p1) and G.has_edge(a1, p3) and
             not(G.has_edge(a2, p3)) and not(G.has_edge(a1, p1)))):
             return 1
        return -1
    else:
        return -1
    
class OneThreeMotifClassificator(MotifClassificator):
    """
    :py:class:`sma.MotifClassificator` for classifying (1,3)-motifs.
    """
    def __call__(self, motif):
        return classify13Motif(self.G, motif)
    def info(self):
        return sma.Motif13Info
    
def classify13Motif(G : nx.Graph, motif) -> int:
    a, b1, b2, b3 = motif
    if not G.has_edge(b1, b3):
        c1, c2, c3 = b1, b2, b3
    elif not G.has_edge(b1, b2):
        c1, c2, c3 = b1, b3, b2
    elif not G.has_edge(b2, b3):
        c1, c2, c3 = b2, b1, b3
    else:
        return -1
    if G.has_edge(a, c1) and G.has_edge(c1, c2) and G.has_edge(c2, c3) and G.has_edge(c3, a):
        return 1
    return -1
    

    
class MultiMotifClassificator(MotifClassificator):
    """
    :py:class:`sma.MotifClassificator` for classifying multi-motifs. This class
    is a wrapper class for several other motif classificators. Based on the given
    arities, i.e. the numbers of nodes from the different levels of the SEN, a
    suitable classificator is choosen automatically. This means that depending on
    the given parameters, the number of classes and their names is different.
    
    See the documentation or query the motif database with :py:meth:`sma.motifInfo`
    and :py:meth:`sma.supportedSignatures` for a full list of supported motifs.
    
    Every instances of this class is aware of the names and amount of classes that
    it uses for classification.
    
    See also :py:meth:`sma.matchPositions` and :py:meth:`sma.multiSignature` for
    a description of the internal position matching mechanisms
    
    :param arities: arities
    :param roles: list of indices
    :raises NotSupportedError: whenever there is no matching classificator available
    """
    def __init__(self, G : nx.Graph, *arities : int, roles = []):
        super().__init__(G)
        self.arities = arities
        self.roles = roles
        signature_ordered = sma.multiSignature(arities)
        self.motif_info = sma.motifInfo(signature_ordered, G.is_directed())
        self.signature = self.motif_info.signature
        self.positions = sma.matchPositions(self.signature, arities, roles)
        # initialize classificator
        self.classificator = self.motif_info.classificator(self.G)
    def __call__(self, motif):
        twisted_motif = []
        for p in self.positions:
            twisted_motif += motif[p]
        return self.classificator(twisted_motif)
    def __str__(self):
        return 'MultiMotifClassificator%s' % str(self.signature)
    def info(self):
        return self.motif_info

# Underneath you find very messy classificators for multi-motifs.

class Multi111MotifClassificator(MotifClassificator):
    def __call__(self, motif):
        return classify111Motif(self.G, motif)
    def info(self):
        return sma.Motif111Info

def classify111Motif(G : nx.Graph, motif) -> int:
    a, b, c = motif
    return 4 * G.has_edge(a,c) + 2 * G.has_edge(b, c) + G.has_edge(a, b)

class Multi121MotifClassificator(MotifClassificator):
    def __call__(self, motif):
        return classify121Motif(self.G, motif)
    def info(self):
        return sma.Motif121Info

def classify121Motif(G : nx.Graph, motif) -> int:
    a, b1, b2, c = motif
    if G.has_edge(b1, c) and G.has_edge(b2, c):
        if G.has_edge(a, c) and G.has_edge(b1, a) and G.has_edge(b2, a):
            # induced subgraphs {a, b1, c} and {a, b2, c} complete
            if G.has_edge(b1, b2):
                return 4 # Ohio E closed
            else:
                return 3 # Ohio E open
        if not(G.has_edge(b1, b2)) and not(G.has_edge(a,c)):
            t = G.has_edge(a, b1) + G.has_edge(a, b2)
            if t == 1:
                return 1 # (i)
            elif t == 2:
                return 2 # (h)
    return -1

class Multi221MotifClassificator(MotifClassificator):
    def __call__(self, motif):
        return classify221Motif(self.G, motif)
    def info(self):
        return sma.Motif221Info

def classify221Motif(G : nx.Graph, motif) -> str:
    a1, a2, b1, b2, c = motif
    if G.has_edge(a1, c) ^ G.has_edge(a2, c):
        return 'Unclassified'
    if G.has_edge(b1, c) ^ G.has_edge(b2, c):
        return 'Unclassified'
    block4 = classify4Motif(G, (a1, a2, b1, b2))
    if G.has_edge(a1, c):
        if G.has_edge(b1, c):
            return '%s.%d' % (block4, 3) # both bound
        else:
            return '%s.%d' % (block4, 1) # only (a) bound
    else:
        if G.has_edge(b1, c):
            return '%s.%d' % (block4, 2) # only (b) bound
        else:
            return '%s.%d' % (block4, 0) # nothing bound
    return 'Unclassified'

class Multi222MotifClassificator(MotifClassificator):
    def __call__(self, motif):
        return classify222Motif(self.G, motif)
    def info(self):
        return sma.Motif222Info    

def classify222Motif(G : nx.Graph, motif) -> int:
    a1, a2, b1, b2, c1, c2 = motif
    if G.has_edge(b1, b2) or not(G.has_edge(c1,c2)):
        return -1
    AC = (G.has_edge(a1, c1) + G.has_edge(a2, c2) +
          G.has_edge(a1, c2) + G.has_edge(a2, c1))
    if AC == 4: # all a-c edges are there
        if (G.has_edge(a1, b1) and G.has_edge(a2, b2) and
            G.has_edge(a1, b2) and G.has_edge(a2, b1) and
            G.has_edge(b1, c1) and G.has_edge(b2, c2) and
            G.has_edge(b1, c2) and G.has_edge(b2, c1)):
            if G.has_edge(a1, a2):
                return 4 # Ohio H closed
            else:
                return 3 # Ohio H open
        return -1
    elif AC == 0: # no a-c edges
        if not(G.has_edge(a1, b1)): # swap b1 and b2 
            h = b1
            b1 = b2
            b2 = h
        if not(G.has_edge(b1, c1)): # swap c1 and c2
            h = c1
            c1 = c2
            c2 = h
        if (G.has_edge(a1, b1) and G.has_edge(b1, c1) and
            G.has_edge(a2, b2) and G.has_edge(b2, c2) and
            not(G.has_edge(a1, b2)) and not(G.has_edge(a2, b1)) and
            not(G.has_edge(b1, c2)) and not(G.has_edge(b2, c1))):
            if G.has_edge(a1, a2):
                return 2 # (m)
            else:
                return 1 # (n)
    return -1
