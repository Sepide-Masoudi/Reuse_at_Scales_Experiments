#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import networkx as nx
import numpy
import scipy

import sma

def count3pMotifsLinalg(G : nx.Graph, 
                        level, 
                        array : bool = False,
                        progress_report : bool = False):
    """
    Counter for plain 3-motifs using linear algebra.
    
    This function counts plain 3-motifs not by enumerating and classifying all
    of them but by using linear algebra.
    
        1. The adjacency matrix :math:`A` of the level of interest is extracted.
        2. The adjacency matrix powers :math:`A^2` and :math:`A^3` are computed.
        3. The number of motifs of type 3 (closed triangles) is given by 
           :math:`\operatorname{tr}(A^3)/6`.
        4. The number of motifs of type 2 (3-paths) is given by the sum of those
           upper triangular entries of :math:`A^2` where :math:`A` is zero.
        5. The number of motifs of type 1 (2-cliques) is given by the difference of
           total number of edges times the number of vertices minus 2 and twice
           the number of type-2-motifs and the three times the number of 3-motifs.
        6. The number of motifs of type 0 (cocliques) is the remaining number of
           motifs.
    
    The function runs in subcubic time in the number of vertices.
    
    :param G: the network
    :param level: sesType of the level
    :param array: whether an array should be returned
    :param progress_report: dummy parameter (progress reports not supported by
        ad hoc counters)
    """
    adj = nx.to_numpy_array(G, nodelist=list(sma.sesSubgraph(G, level)), dtype=int)
    adj2 = adj @ adj
    adj3 = adj2 @ adj
    edges = numpy.sum(adj) // 2
    total = scipy.special.comb(len(adj), 3, exact = True)
    motif3 = numpy.trace(adj3) // 6
    motif2 = (numpy.sum(adj2[adj == 0]) - numpy.sum(numpy.diag(adj2))) // 2
    motif1 = (len(adj) - 2) * edges - 2 * motif2 - 3 * motif3
    motif0 = total - motif1 - motif2 - motif3
    result = {0: motif0,
              1: motif1,
              2: motif2,
              3: motif3}
    if array:
        return numpy.array([result[k] for k in range(4)])
    return result

def count2pMotifs(G : nx.Graph, 
                  level, 
                  array : bool = False,
                  progress_report : bool = False):
    """
    Counts the number of plain 2-motifs by simply accessing the number of vertices
    and edges in the network on the respective level.
    
    :param G: the network
    :param level: sesType of the level
    :param array: whether an array should be returned
    :param progress_report: dummy parameter (progress reports not supported by
        ad hoc counters)
    """
    subgraph = G.subgraph(sma.sesSubgraph(G, level))
    edges = subgraph.number_of_edges()
    other = scipy.special.comb(subgraph.number_of_nodes(), 2, exact = True) - edges
    if array:
        return numpy.array([other, edges])
    else:
        return {0 : other, 1 : edges}