#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import itertools, functools
import scipy.special
import numpy
import networkx as nx
import sma

def triangleCoefficient(G : nx.Graph, node, othertype = None) -> float:
    """
    Calculates the triangle coefficient of node, which is defined as follows:
    
    Take all 3-motifs with the node as distinct node and compute the number of 
    I.C and II.C motifs (open and closed triangles with the given node at the point).
    Divide the number of I.C motifs by the sum of number of I.C motifs and II.C motifs.
    
    See :py:meth:`sma.cooccurrenceTable` for a more general function.
    
    :param G: the graph
    :param node: the node whose triangle coefficient shall be computed
    :param othertype: the ``sesType`` of the non-distinct nodes or ``None`` if all
        nodes with ``sesType`` different from the ``sesType`` of the distinct node
        shall be considered. A value must be specified when used with multi-level
        networks in order to avoid unexpected behaviour.
    :returns: II.C / (I.C + II.C), i.e. the ratio of closed triangles vs. all triangles,
        if no triangles are found, this function returns zero.
    """
    neighbors = G[node]
    nodesType = G.nodes[node]['sesType']
    check = lambda n : G.nodes[n]['sesType'] != nodesType
    if othertype is not None:
        check = lambda n : G.nodes[n]['sesType'] == othertype
    neighborsOtherType = list(filter(check, neighbors))
    countTriangles = scipy.special.binom(len(neighborsOtherType), 2)
    if countTriangles == 0:
        return 0
    countClosedTriangles = sum(map(lambda pair: G.has_edge(*pair), itertools.combinations(neighborsOtherType, 2)))
    return countClosedTriangles / countTriangles

def triangleCoefficients(G : nx.Graph, array : bool = False):
    """
    Computes the triangle coefficients for all nodes in a graph.
    
    :param G: the graph
    :param array: set array to True if you want the result as a list instead of a dict
    
    See :py:meth:`sma.triangleCoefficient` for details.
    """
    if array:
        return numpy.fromiter((triangleCoefficient(G, node) for node in G.nodes), dtype = float)
    else:
        return {node : triangleCoefficient(G, node) for node in G.nodes}

def connectedOpposingSystem(G : nx.Graph, node, othertype = None) -> set:
    """
    Returns the set of nodes which are connected to the given node but have the
    opposite social-ecological type.
    
    :param G: the graph
    :param node: the node
    :param othertype: the ``sesType`` of the opposite nodes or ``None`` if all
        nodes with ``sesType`` different from the ``sesType`` of the specified node
        shall be considered. A value must be specified when used with multi-level
        networks in order to avoid unexpected behaviour.
    :returns: set of nodes which share edges with the given node and are of the 
        other social-ecological type.
    """
    neighbors = G[node]
    nodesType = G.nodes[node]['sesType']
    check = lambda n : G.nodes[n]['sesType'] != nodesType
    if othertype is not None:
        check = lambda n : G.nodes[n]['sesType'] == othertype
    neighborsOtherType = set(filter(check, neighbors))
    return neighborsOtherType

def overlappingCoefficients(G : nx.Graph, subsystem : int = sma.NODE_TYPE_ECO) -> numpy.ndarray:
    """
    Returns a matrix of overlapping coefficients for a given subsystem of nodes.
    For two nodes :math:`x`, :math:`y` of the same type the overlapping coefficient is defined as
    
    .. math ::
        
        O(x,y) = \\begin{cases}
                    \\frac{|S(x) \cap S(y)|}{|S(x) \cup S(y)|}, & \\text{if } S(x) \cup S(y) \\neq \\emptyset \\\\
                    0, & \\text{otherwise} \\
                 \\end{cases}
        
    where :math:`O(x,y)` is the overlapping coefficient of :math:`x` and :math:`y` and :math:`S(i)` 
    is the connected opposing system of :math:`i`, cf. :py:meth:`sma.connectedOpposingSystem`, i.e. the 
    set of nodes which are connected to :math:`i` but are of the opposite social ecological
    type.
    
    :param G: the graph
    :param subsystem: type of the nodes to compute the coefficients for, default is
        :py:const:`sma.NODE_TYPE_ECO`.
    :returns: symmetric matrix containing the coefficients, default is
        :py:const:`sma.NODE_TYPE_ECO` for computing the overlapping coefficients
        of the ecological subsystem
    
    """
    nodes = list(sma.sesSubgraph(G, subsystem))
    result = numpy.identity(len(nodes))
    opposingSystems = list(map(functools.partial(connectedOpposingSystem, G), nodes))
    
    for i in range(len(nodes)):
        A = opposingSystems[i]
        if len(A) == 0:
            continue
        for j in range(i):
            if G.has_edge(nodes[i], nodes[j]):
                B = opposingSystems[j]
                result[i,j] = result[j, i] = len(A.intersection(B))/ len(A.union(B))
        
    return result