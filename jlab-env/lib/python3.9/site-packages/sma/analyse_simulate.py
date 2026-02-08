#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sma
import itertools
import networkx as nx
import multiprocessing

class _simulateBaselineAutoMapper:
    def __init__(self, motifs, assume_sparse):
        self.motifs = motifs
        self.assume_sparse = assume_sparse
    def __call__(self, G):
        partial, _ = sma.countMotifsAuto(G, *self.motifs, assume_sparse = self.assume_sparse)
        return partial

def simulateBaselineAuto(G : nx.Graph, 
                         *motifs, 
                         n : int= 100,
                         processes : int = 0,
                         chunksize : int = 100,
                         assume_sparse : bool = False,
                         model : str = sma.MODEL_ERDOS_RENYI,
                         level : int = -1) -> dict:
    """
    Simulates a random baseline of graphs similar to a given SEN and counts motifs
    in these randomly generated graphs.
    
    See :py:meth:`sma.randomSimilarMultiSENs` for a documentation of the various
    baseline models.
    
    :param G: the SEN
    :param motifs: motif identifier strings of motifs that shall be counted
    :param n: number of iterations
    :param processes: number of processes, default zero (no multiprocessing)
    :param chunksize: chunksize for multiprocessing
    :param assume_sparse: whether the random graphs shall be assumed to be sparse.
        Used to find an ideal counter, cf. :py:meth:`sma.findIdealCounter`.
    :param model: model to be used, default :py:const:`sma.MODEL_ERDOS_RENYI`.
    :param level: ``sesType`` for Actor's Choice model, 
        see :py:meth:`sma.randomMultiSENsActorsChoice`.
    :returns: dict mapping motif identifiers to list of counts
    """
    random_networks = sma.randomSimilarMultiSENs(G, model = model, level = level)
    source = itertools.islice(random_networks, n)
    mapper = _simulateBaselineAutoMapper(motifs, assume_sparse)
    result = {k : [] for k in motifs}
    if processes <= 0:
        for row in map(mapper, source):
            for k, v in row.items():
                result[k].append(v)
            del row
    else:
        with multiprocessing.Pool(processes) as p:
            rows = p.imap_unordered(mapper, source, chunksize = chunksize)
            for row in rows:
                for k, v in row.items():
                    result[k].append(v)
                del row
            p.close()
            p.join()        
    return result
                
            
    