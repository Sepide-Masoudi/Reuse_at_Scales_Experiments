#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sma
import networkx as nx
from scipy.special import binom
import numpy
import functools, itertools

def _probability(edges, sym, maxedges, probs):
    prob = sym
    for e, p, m in zip(edges, probs, maxedges):
        prob *= p**e * (1-p)**(m-e)
    return prob

def expectedMultiMotifs(G : nx.Graph,
                        *arities, 
                        roles = [],
                        **kwargs):
    """
    Front-end function for several functions for computing motif expectations. It supports
    the same parameters for defining the motifs (arities, roles) as other multi-level
    (counting) functions. Check the documentations of the respective functions.
    The supported functions are:
        
        - :py:meth:`sma.expected3Motifs`,
        - :py:meth:`sma.expected4Motifs`,
        - :py:meth:`sma.expected121Motifs`,
        - :py:meth:`sma.expected221Motifs`,
        - :py:meth:`sma.expected222Motifs`.
    
    See the documentation for an exposition of the mathematical background.
    
    :param G: the SEN
    :param arities: arities of the motifs, cf. :py:class:`sma.MultiMotifClassificator`.
    :param roles: roles of the levels, cf. :py:class:`sma.MultiMotifClassificator`.
    :param kwargs: additional parameters for the functions, see above.
    """
    signature  = sma.multiSignature(arities)
    motif_info = sma.motifInfo(signature, G.is_directed())
    positions  = sma.matchPositions(motif_info.signature, arities, roles)
    if motif_info.expectations is None:
        raise NotImplementedError("expectations for %s-motifs not implemented" % str(motif_info.signature))
    return motif_info.expectations(G, *positions, **kwargs)
    
def varMultiMotifs(G : nx.Graph,
                        *arities, 
                        roles = [],
                        **kwargs):
    """
    Front-end function for several functions for computing motif variances. It supports
    the same parameters for defining the motifs (arities, roles) as other multi-level
    (counting) functions. Check the documentations of the respective functions.
    The supported functions are:
        
        - :py:meth:`sma.var3Motifs`,
        - :py:meth:`sma.var4Motifs`.
    
    See the documentation for an exposition of the mathematical background.
    
    :param G: the SEN
    :param arities: arities of the motifs, cf. :py:class:`sma.MultiMotifClassificator`.
    :param roles: roles of the levels, cf. :py:class:`sma.MultiMotifClassificator`.
    :param kwargs: additional parameters for the functions, see above.
    """
    signature  = sma.multiSignature(arities)
    motif_info = sma.motifInfo(signature, G.is_directed())
    positions  = sma.matchPositions(motif_info.signature, arities, roles)
    if motif_info.variances is None:
        raise NotImplementedError("variances for %s-motifs not implemented" % str(motif_info.signature))
    return motif_info.variances(G, *positions, **kwargs)

def distributionMotifsAuto(G : nx.Graph, 
                           *motifs : str, 
                           model : str = sma.MODEL_ERDOS_RENYI,
                           level : int = -1):
    """
    Front-end function for functions in sma which provide insight into the distribution
    of motif counts in various baseline models.
    
    This function returns a tuple consisting of two dicts:
        
        1. a dict of partial results as requested using the motif identifiers. This
           dict maps motif identifiers to tuples containing firstly the expectation
           and secondly the variance of this motif.
        2. a dict of the results of all motifs with same arities/roles as the motif
           specified using the motif identifiers. This dict maps the heads of the
           motif identifiers to dicts mapping motif classes to tuples of expectations
           and variances as above.
           
    Values which are not available in the selected model are given as ``None``.
    
    The following models (specify using parameter ``model``) are supported:
        
        - ``erdos_renyi`` (default) general Erdős-Rényi random graphs with fixed
          edge probabilities for each subsystem equalling the densities of the 
          given SEN, see documentation, cf. :py:const:`sma.MODEL_ERDOS_RENYI`.
        - ``actors_choice`` edges in one specific level are chosen at random. The
          remainder of the network is fixed. The edge probability in the variable
          level is extracted from the given SEN. Use parameter ``level`` to specify
          the ``sesType`` of the variable level. If :math:`-1` (default), then
          the first entry equalling :math:`2` in the list of arities is selected,
          cd. :py:const:`sma.MODEL_ACTORS_CHOICE`.
    
    :param G: the SEN
    :param motifs: motif identifier strings
    :param model: model to be used
    :param level: additional parameter for model ``actors_choice``
    :returns: tuple of two dicts as above
    :raises ValueError: when the motif identifiers cannot be parsed
    :raises NotImplementedError: if the specified model is not supported
    """
    grouped_request = sma.groupMotifIdentifiers(*motifs)
    partial_results = {}
    total_results = {}
    for head in grouped_request.keys():
        arities, roles, _ = sma.parseMotifIdentifier(head)
        signature  = sma.multiSignature(arities)
        motif_info = sma.motifInfo(signature, G.is_directed())
        if model == sma.MODEL_ERDOS_RENYI:
            expectations = expectedMultiMotifs(G, *arities, roles = roles)
            variances = None
            try:
                variances = varMultiMotifs(G, *arities, roles = roles)
            except NotImplementedError:
                # variance is not implemented for most motifs, so better pass
                pass
            total_results[head] = {k : (expectations[k] if expectations is not None else None, variances[k] if variances is not None else None) for k in expectations.keys()}
        elif model == sma.MODEL_ACTORS_CHOICE:
            total_results[head]  = distributionMotifsActorsChoice(G,
                                                                    *arities,
                                                                    roles = roles,
                                                                    level = level,
                                                                    array = False)
        else:
            raise NotImplementedError("model %s not supported" % model)
        for motif in grouped_request[head]:
            key = motif_info.classes_type(motif)
            try:
                partial_results["%s[%s]" % (head, motif)] = total_results[head][key]
            except KeyError:
                raise ValueError("Unrecognizable motif identifier %s[%s]." % (head, motif))
    return (partial_results, total_results)
    
def expected3Motifs(G : nx.Graph, 
                    level0, 
                    level1, 
                    array = False, 
                    densities : bool = False):
    """
    Computes the expected number of 3-motifs in a SEN. See the documentation for an
    exposition of the mathematical background.
    
    Use functions :py:meth:`sma.expected3EMotifs` and :py:meth:`sma.expected3SMotifs`
    for regular two level graphs.
    
    If ``densities = True``, the returned values sum up to one. Otherwise their
    sum is total number of 3-motifs, see :py:meth:`sma.total3EMotifs` etc.
    
    :param G: the SEN
    :param level0: ``sesType`` of the distinct node, e.g. in 3E-motifs :py:const:`sma.NODE_TYPE_ECO`
    :param level1: ``sesType`` of the other nodes, e.g. in 3E-motifs :py:const:`sma.NODE_TYPE_SOC`
    :param array: whether the result shall be an array or a dict
    :param densities: whether densities or absolute numbers of motifs shall be returned
    """
    v = sma.nodesCount(G)
    d = sma.densityMatrix(G)
    
    total = 1 if densities else binom(v[level1], 2) * v[level0]
    p0 = d[level0, level1] if level0 <= level1 else d[level1,level0]
    p1 = d[level1, level1]
    
    maxedges = numpy.max(sma.MOTIF3_EDGES, axis = 0)
    res = list(itertools.starmap(functools.partial(_probability, maxedges = maxedges, probs = [p1, p0]),
                  zip(sma.MOTIF3_EDGES, sma.MOTIF3_AUT)))
    results = total * numpy.array(res)
    if not array:
        return {k : v for k,v in zip(sma.MOTIF3_NAMES, results)}
    return results

def expected4Motifs(G : nx.Graph, 
                    level0 : int = sma.NODE_TYPE_SOC, 
                    level1 : int = sma.NODE_TYPE_ECO, 
                    array : bool = False, 
                    densities : bool = False):
    """
    Computes the expected number of 4-motifs in a SEN. See the documentation for an
    exposition of the mathematical background.
    
    If ``densities = True``, the returned values sum up to one. Otherwise their
    sum is total number of 4-motifs, see :py:meth:`sma.total4Motifs` etc.
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper nodes, standard :py:const:`sma.NODE_TYPE_SOC`
    :param level1: ``sesType`` of the lower nodes, e.g. in 3E-motifs :py:const:`sma.NODE_TYPE_ECO`
    :param array: whether the result shall be an array or a dict
    :param densities: whether densities or absolute numbers of motifs shall be returned
    """
    v = sma.nodesCount(G)
    d = sma.densityMatrix(G)
    
    total = 1 if densities else binom(v[level1], 2) * binom(v[level0], 2)
    p0 = d[level0, level0]
    p1 = d[level0, level1] if level0 <= level1 else d[level1,level0]
    p2 = d[level1, level1]
    maxedges = numpy.max(sma.MOTIF4_EDGES, axis = 0)

    res = list(itertools.starmap(functools.partial(_probability, maxedges = maxedges, probs = [p0, p1, p2]),
                  zip(sma.MOTIF4_EDGES, sma.MOTIF4_AUT)))
    results = total * numpy.array(res)
    if not array:
        return {k : v for k,v in zip(sma.MOTIF4_NAMES, results)}
    return results

def expected3EMotifs(G : nx.Graph, **kwargs):
    """
    Computes the expected number of 3E-motifs in a SEN. See the documentation for an
    exposition of the mathematical background. See also :py:meth:`sma.expected3Motifs`.
    
    :param G: the SEN
    :param kwargs: additional parameters for :py:meth:`sma.expected3Motifs`.
    """
    return expected3Motifs(G, sma.NODE_TYPE_ECO, sma.NODE_TYPE_SOC, **kwargs)
def expected3SMotifs(G : nx.Graph, **kwargs):
    """
    Computes the expected number of 3S-motifs in a SEN. See the documentation for an
    exposition of the mathematical background. See also :py:meth:`sma.expected3Motifs`.
    
    :param G: the SEN
    :param kwargs: additional parameters for :py:meth:`sma.expected3Motifs`.
    """
    return expected3Motifs(G, sma.NODE_TYPE_SOC, sma.NODE_TYPE_ECO, **kwargs)

def expected121Motifs(G : nx.Graph, 
                      level0 : int, 
                      level1 : int, 
                      level2 : int,
                      array : bool = False,
                      density : bool = False):
    """
    Computes the expected number of multi level motifs with arities 1, 2, 1. 
    See the documentation for an exposition of the mathematical background.
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper node
    :param level1: ``sesType`` of the middle nodes
    :param level2: ``sesType`` of the lower node
    :param array: whether the result shall be an array or a dict
    :param densities: whether densities or absolute numbers of motifs shall be returned
    """
    v = sma.nodesCount(G)
    d = sma.densityMatrix(G)
    
    total = 1 if density else v[level0] * binom(v[level1], 2) * v[level2]
    p01 = d[level0, level1] if level0 <= level1 else d[level1,level0]
    p02 = d[level0, level2] if level0 <= level2 else d[level2,level0]
    p11 = d[level1, level1]
    p12 = d[level1, level2] if level1 <= level2 else d[level2,level1]
    results = numpy.array([
            0,
            2 * p01 * (1-p01) * (1-p11) * p12**2 * (1-p02),
            p01**2 * (1-p11) * p12**2 * (1-p02),
            p01**2 * (1-p11) * p12**2 * p02,
            p01**2 * p11 * p12**2 * p02,
        ])
    results[0] = 1 - sum(results)
    results = total * results
    if array:
        return results
    return {k : r for k, r in zip([-1,1,2,3,4], results)}

def expected221Motifs(G : nx.Graph, 
                      level0 : int, 
                      level1 : int, 
                      level2 : int, 
                      array : bool = False,
                      density : bool = False):
    """
    Computes the expected number of multi level motifs with arities 2, 2, 1. 
    See the documentation for an exposition of the mathematical background.
    
    Uses :py:meth:`sma.expected4Motifs` for computing the expectations of the upper
    part.
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper node
    :param level1: ``sesType`` of the middle nodes
    :param level2: ``sesType`` of the lower node
    :param array: whether the result shall be an array or a dict
    :param densities: whether densities or absolute numbers of motifs shall be returned
    """
    v = sma.nodesCount(G)
    d = sma.densityMatrix(G)
    
    total = 1 if density else binom(v[level0], 2) * binom(v[level1], 2) * v[level2]
    p02 = d[level0, level2] if level0 <= level2 else d[level2,level0]
    p12 = d[level1, level2] if level1 <= level2 else d[level2,level1]
    
    values4 = sma.expected4Motifs(G, level0, level1, array = True, densities = True)
    
    factors = [
            (1-p02)**2 * (1-p12)**2,
            p02**2 * (1-p12)**2,
            (1-p02)**2 * p12**2,
            p02**2 * p12**2,
        ]
    result = {'Unclassified' : 0, **{
            '%s.%d' % (m, i) : total * f * v
            for (m, v), (i, f) in itertools.product(zip(sma.MOTIF4_NAMES, values4), zip([0, 1, 2, 3], factors))
        }}
    result['Unclassified'] = total - sum(result.values())
    if array:
        return numpy.array(list(result.values()))
    return result

def expected222Motifs(G : nx.Graph, 
                      level0 : int, 
                      level1 : int, 
                      level2 : int, 
                      array : bool = False,
                      density : bool = False):
    """
    Computes the expected number of multi level motifs with arities 2, 2, 2. 
    See the documentation for an exposition of the mathematical background.
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper node
    :param level1: ``sesType`` of the middle nodes
    :param level2: ``sesType`` of the lower node
    :param array: whether the result shall be an array or a dict
    :param densities: whether densities or absolute numbers of motifs shall be returned
    """
    v = sma.nodesCount(G)
    d = sma.densityMatrix(G)
    
    total = 1 if density else binom(v[level0], 2) * binom(v[level1], 2) * binom(v[level2], 2)
    p00 = d[level0, level0]
    p01 = d[level0, level1] if level0 <= level1 else d[level1,level0]
    p02 = d[level0, level2] if level0 <= level2 else d[level2,level0]
    p11 = d[level1, level1]
    p12 = d[level1, level2] if level1 <= level2 else d[level2,level1]
    p22 = d[level2, level2]

    results = numpy.array([
            0,
            2 * (1-p00) * (1-p01)**2 * p01**2 * (1-p12)**2 * (1-p11) * p12**2 * p22 * (1-p02)**4,
            2 * p00 * (1-p01)**2 * p01**2 * (1-p12)**2 * (1-p11) * p12**2 * p22 * (1-p02)**4,
            (1-p00) * p01**4 * p02**4 * (1-p11) * p12**4 * p22,
            p00 * p01**4 * p02**4 * (1-p11) * p12**4 * p22
        ])
    results[0] = 1 - sum(results)
    results = total * results
    if array:
        return results
    return {k : r for k, r in zip([-1,1,2,3,4], results)}

def expected111Motifs(G : nx.Graph,
                      level0 : int,
                      level1 : int,
                      level2 : int,
                      array : bool = False,
                      density : bool = False):
    """
    Computes the expected number of multi level motifs with arities 2, 2, 2. 
    See the documentation for an exposition of the mathematical background.
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper node
    :param level1: ``sesType`` of the middle nodes
    :param level2: ``sesType`` of the lower node
    :param array: whether the result shall be an array or a dict
    :param densities: whether densities or absolute numbers of motifs shall be returned
    """
    v = sma.nodesCount(G)
    d = sma.densityMatrix(G)
    
    total = 1 if density else v[level0] * v[level1] * v[level2]
    p01 = d[level0, level1] if level0 <= level1 else d[level1,level0]
    p02 = d[level0, level2] if level0 <= level2 else d[level2,level0]
    p12 = d[level1, level2] if level1 <= level2 else d[level2,level1]
    
    results = total * numpy.array([
            (1-p01) * (1-p12) * (1-p02),
            p01     * (1-p12) * (1-p02),
            (1-p01) * p12     * (1-p02),
            p01     * p12     * (1-p02),
            (1-p01) * (1-p12) * p02,
            p01     * (1-p12) * p02,
            (1-p01) * p12     * p02,
            p01     * p12     * p02
            ])
    
    if array:
        return results
    return {k : r for k, r in zip(range(8), results)}

def var3Motifs(G : nx.Graph, 
               level0 : int, 
               level1 : int, 
               array : bool = False,
               second_moment : bool = False):
    """
    Computes variances of the number for 3-motifs in a SEN. See documentation for
    the mathematical background.
    
    This function uses the following formula where :math:`X` denotes the random
    variable number of 3-motifs
    
    .. math::
        
        \mathbb{V}[X] = \mathbb{E}[X^2] - (\mathbb{E}[X])^2
        
    
    and computes the expectation using :py:meth:`sma.expected3Motifs`. Set
    ``second_moment = True`` to compute :math:`\mathbb{E}[X^2]` instead of the variance.
    In this case :py:meth:`sma.expected3Motifs` is not called.
    
    :param G: the SEN
    :param level0: ``sesType`` of the distinct node, e.g. in 3E-motifs :py:const:`sma.NODE_TYPE_ECO`
    :param level1: ``sesType`` of the other nodes, e.g. in 3E-motifs :py:const:`sma.NODE_TYPE_SOC`
    :param array: whether the result should be an array instead of a dict
    :param second_moment: switch on for computing the second moment instead of the
        variance
    """
    d = sma.densityMatrix(G)
    v = sma.nodesCount(G)
    
    p0 = d[level0, level1] if level0 <= level1 else d[level1,level0]
    p1 = d[level1, level1]
    v0 = v[level0]
    v1 = v[level1]     
    partition = numpy.array([
                 v0 * binom(v1,2),                           # all nodes shared
                 v0 * v1 * (v1-1) * (v1-2),                  # one from each level shared
                 binom(v1, 2) * v0 * (v0-1),                 # two from non-distinct level shared
                 v0 * v1 * (v0-1) * (v1-1) * (v1-2),         # one non-distinct node shared
                 v0 * binom(v1,2) * binom(v1-2,2),           # distinct node shared
                 v0 * (v0-1) * binom(v1,2) * binom(v1-2,2)   # no nodes shared
            ])
    # one column for each entry in partition, see above
    # one row for each motif I.A-II.C
    motifprops = numpy.array([
                [(1-p0)**2 * (1-p1), (1-p0)**3*(1-p1)**2,                   (1-p0)**4 * (1-p1),        (1-p0)**4 * (1-p1)**2,       (1-p0)**4 * (1-p1)**2,       (1-p0)**4 * (1-p1)**2],
                [2*(1-p0)*(1-p1)*p0, (1-p1)**2*((1-p0)**2*p0+p0**2*(1-p0)), 4*(1-p0)**2*p0**2 *(1-p1), 4*(1-p0)**2*p0**2*(1-p1)**2, 4*(1-p0)**2*p0**2*(1-p1)**2, 4*(1-p0)**2*p0**2*(1-p1)**2],
                [p0**2*(1-p1),       p0**3*(1-p1)**2,                       p0**4*(1-p1),              p0**4*(1-p1)**2,             p0**4*(1-p1)**2,             p0**4*(1-p1)**2],
                [(1-p0)**2 *p1,      (1-p0)**3*p1**2,                       (1-p0)**4*p1,              (1-p0)**4 * p1**2,           (1-p0)**4 * p1**2,           (1-p0)**4 * p1**2],
                [2*(1-p0)*p1*p0,     p1**2*((1-p0)**2*p0+p0**2*(1-p0)),     4*(1-p0)**2*p0**2 * p1,    4*(1-p0)**2*p0**2*p1**2,     4*(1-p0)**2*p0**2*p1**2,     4*(1-p0)**2*p0**2*p1**2],
                [p0**2*p1,           p0**3*p1**2,                           p0**4*p1,                  p0**4*p1**2,                 p0**4*p1**2,                 p0**4*p1**2]
            ])
    if second_moment:
        result = motifprops @ partition
    else:
        expectations = expected3Motifs(G, level0, level1, array=True)
        result = motifprops @ partition - expectations**2
    if array:
        return result
    else:
        return {k : v for k, v in zip(sma.MOTIF3_NAMES, result)}

def var3EMotifs(G : nx.Graph, **kwargs):
    """
    Computes the variance of the number of 3E-motifs in a SEN. See the documentation for a
    exposition of the mathematical background. See also :py:meth:`sma.expected3Motifs`.
    
    :param G: the SEN
    :param kwargs: additional parameters for :py:meth:`sma.var3Motifs`.
    """
    return var3Motifs(G, sma.NODE_TYPE_ECO, sma.NODE_TYPE_SOC, **kwargs)

def var3SMotifs(G : nx.Graph, **kwargs):
    """
    Computes the variance of the number of 3S-motifs in a SEN. See the documentation for a
    exposition of the mathematical background. See also :py:meth:`sma.expected3Motifs`.
    
    :param G: the SEN
    :param kwargs: additional parameters for :py:meth:`sma.var3Motifs`.
    """
    return var3Motifs(G, sma.NODE_TYPE_SOC, sma.NODE_TYPE_ECO, **kwargs)
  
def var4Motifs(G : nx.Graph, 
               level0 : int = sma.NODE_TYPE_SOC, 
               level1 : int = sma.NODE_TYPE_ECO, 
               array : bool = False,
               second_moment : bool = False):
    """
    Variances for the number of 4-motifs. See the documentation for a
    exposition of the mathematical background.
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper nodes, standard :py:const:`sma.NODE_TYPE_SOC`
    :param level1: ``sesType`` of the lower nodes, e.g. in 3E-motifs :py:const:`sma.NODE_TYPE_ECO`
    :param array: whether the result shall be an array or a dict    
    :param second_moment: switch on for computing the second moment instead of the
        variance
    """
    d = sma.densityMatrix(G)
    v = sma.nodesCount(G)
    
    p0 = d[level0, level0]
    p1 = d[level0, level1] if level0 <= level1 else d[level1, level0]
    p2 = d[level1, level1]
    v0 = v[level0]
    v1 = v[level1]
    
    partition = numpy.array([
            binom(v0, 2) * binom(v1, 2),
            binom(v0, 2) * v1 * (v1 - 1) * (v1 - 2),
            binom(v1, 2) * v0 * (v0 - 1) * (v0 - 2),
            v0 * v1 * (v0 - 1) * (v1 - 1) * (v0 - 2) * (v1 - 2),
            binom(v0, 2) * binom(v1 - 2, 2) * binom(v1, 2),
            binom(v1, 2) * binom(v0 - 2, 2) * binom(v0, 2),
            v0 * binom(v1, 2) * binom(v1 - 2, 2) * (v0 - 1) * (v0 - 2),
            v1 * binom(v0, 2) * binom(v0 - 2, 2) * (v1 - 1) * (v1 - 2),
            binom(v0, 2) * binom(v0 - 2, 2) * binom(v1, 2) * binom(v1 - 2, 2)
            ])
    
    expectations = expected4Motifs(G, level0, level1, array = True, densities = True)
    expectations_squared = expectations ** 2
    
    motifprops = numpy.zeros((len(sma.MOTIF4_NAMES), len(partition)))
    # maximal overlap
    motifprops[:, 0] = expectations
    # two top nodes and one bottom node overlapping
    # 6 relevant cross-level edges
    motifprops12 = numpy.array([
            2 * (1-p1)**3 * p1**3,
            2 * (1-p1)**3 * p1**3,
            2 * (1-p1)**3 * p1**3,
            2 * (1-p1)**3 * p1**3,
            
            (p1**4 * (1-p1)**2 + p1**2 * (1-p1)**4),
            (p1**4 * (1-p1)**2 + p1**2 * (1-p1)**4),
            (p1**4 * (1-p1)**2 + p1**2 * (1-p1)**4),
            (p1**4 * (1-p1)**2 + p1**2 * (1-p1)**4),
            
            p1**6,
            p1**6,
            p1**6,
            p1**6,
            
            (1-p1)**6,
            (1-p1)**6,
            (1-p1)**6,
            (1-p1)**6,
            
            (2 * p1**5 * (1-p1) + 4 * p1**4 * (1-p1)**2),
            (2 * p1**5 * (1-p1) + 4 * p1**4 * (1-p1)**2),
            (2 * p1**5 * (1-p1) + 4 * p1**4 * (1-p1)**2),
            (2 * p1**5 * (1-p1) + 4 * p1**4 * (1-p1)**2),
            
            (4 * p1**2 * (1-p1)**4 + 2 * p1 * (1-p1)**5),
            (4 * p1**2 * (1-p1)**4 + 2 * p1 * (1-p1)**5),
            2 * p1**3 * (1-p1)**3,
            2 * p1**3 * (1-p1)**3,
            
            (4 * p1**2 * (1-p1)**4 + 2 * p1 * (1-p1)**5),
            (4 * p1**2 * (1-p1)**4 + 2 * p1 * (1-p1)**5),
            2 * p1**3 * (1-p1)**3,
            2 * p1**3 * (1-p1)**3
            ])
    factors1 = numpy.array([
            (1-p0) * (1-p2)**2,
            p0     * (1-p2)**2,
            (1-p0) * p2**2,
            p0     * p2**2,
            
            (1-p0) * (1-p2)**2,
            p0     * (1-p2)**2,
            (1-p0) * p2**2,
            p0     * p2**2,
            
            (1-p0) * (1-p2)**2,
            p0     * (1-p2)**2,
            (1-p0) * p2**2,
            p0     * p2**2,
            
            (1-p0) * (1-p2)**2,
            p0     * (1-p2)**2,
            (1-p0) * p2**2,
            p0     * p2**2,
            
            (1-p0) * (1-p2)**2,
            p0     * (1-p2)**2,
            (1-p0) * p2**2,
            p0     * p2**2,
            
            p0 * (1-p2)**2,
            p0 * p2**2,
            p0 * (1-p2)**2,
            p0 * p2**2,
            
            (1-p0) * (1-p2)**2,
            (1-p0) * p2**2,
            (1-p0) * (1-p2)**2,
            (1-p0) * p2**2
            ])
    motifprops[:, 1] = numpy.multiply(motifprops12, factors1)
    # one top node and two bottom nodes overlapping
    # 6 relevant cross-level edges
    factors2 = numpy.array ([
            (1-p0)**2 * (1-p2),
            p0    **2 * (1-p2),
            (1-p0)**2 * p2,
            p0    **2 * p2,
            
            (1-p0)**2 * (1-p2),
            p0    **2 * (1-p2),
            (1-p0)**2 * p2,
            p0    **2 * p2,
            
            (1-p0)**2 * (1-p2),
            p0    **2 * (1-p2),
            (1-p0)**2 * p2,
            p0    **2 * p2,
            
            (1-p0)**2 * (1-p2),
            p0    **2 * (1-p2),
            (1-p0)**2 * p2,
            p0    **2 * p2,
            
            (1-p0)**2 * (1-p2),
            p0    **2 * (1-p2),
            (1-p0)**2 * p2,
            p0    **2 * p2,
            
            p0**2 * (1-p2),
            p0**2 * p2,
            p0**2 * (1-p2),
            p0**2 * p2,
            
            (1-p0)**2 * (1-p2),
            (1-p0)**2 * p2,
            (1-p0)**2 * (1-p2),
            (1-p0)**2 * p2
            ])
    motifprops[:, 2] = numpy.multiply(motifprops12, factors2)
    # one top node and one bottom node overlapping
    # 7 relevant cross-level edges
    motifprops[:, 3] = [
            (1-p0)**2 * (1-p2)**2 * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3),
            p0**2     * (1-p2)**2 * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3),
            (1-p0)**2 * p2**2     * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3),
            p0**2     * p2**2     * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3),
            
            (1-p0)**2 * (1-p2)**2 * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3),
            p0**2     * (1-p2)**2 * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3),
            (1-p0)**2 * p2**2     * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3),
            p0**2     * p2**2     * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3),
            
            (1-p0)**2 * (1-p2)**2 * p1**7,
            p0**2     * (1-p2)**2 * p1**7,
            (1-p0)**2 * p2**2     * p1**7,
            p0**2     * p2**2     * p1**7,
            
            (1-p0)**2 * (1-p2)**2 * (1-p1)**7,
            p0**2     * (1-p2)**2 * (1-p1)**7,
            (1-p0)**2 * p2**2     * (1-p1)**7,
            p0**2     * p2**2     * (1-p1)**7,
            
            (1-p0)**2 * (1-p2)**2 * (9 * p1**5 * (1-p1)**2 + p1**6 * (1-p1)),
            p0**2     * (1-p2)**2 * (9 * p1**5 * (1-p1)**2 + p1**6 * (1-p1)),
            (1-p0)**2 * p2**2     * (9 * p1**5 * (1-p1)**2 + p1**6 * (1-p1)),
            p0**2     * p2**2     * (9 * p1**5 * (1-p1)**2 + p1**6 * (1-p1)),
            
            p0**2     * (1-p2)**2 * (9 * p1**2 * (1-p1)**5 + p1 * (1-p1)**6),
            p0**2     * p2**2     * (9 * p1**2 * (1-p1)**5 + p1 * (1-p1)**6),
            p0**2     * (1-p2)**2 * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3),
            p0**2     * p2**2     * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3),
            
            (1-p0)**2 * (1-p2)**2 * (9 * p1**2 * (1-p1)**5 + p1 * (1-p1)**6),
            (1-p0)**2 * p2**2     * (9 * p1**2 * (1-p1)**5 + p1 * (1-p1)**6),
            (1-p0)**2 * (1-p2)**2 * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3),
            (1-p0)**2 * p2**2     * (p1**3 * (1-p1)**4 + p1**4 * (1-p1)**3)
            ]
    # two top nodes overlapping
    # 8 relevant cross-level edges
    # same as two independent motifs, just the top edge is counted twice
    factors = p0**sma.MOTIF4_EDGES[:,0] * (1-p0) ** (1- sma.MOTIF4_EDGES[:,0])
    numpy.divide(expectations_squared, factors, where=(factors!=0), out = motifprops[:, 4])
    # two bottom nodes overlapping
    # 8 relevant cross-level edges
    # same as two independent motifs, just the bottom edge is counted twice
    factors = p2**sma.MOTIF4_EDGES[:,2] * (1-p2) ** (1- sma.MOTIF4_EDGES[:,2])
    numpy.divide(expectations_squared, factors, where=(factors!=0), out = motifprops[:, 5])
    # one top node overlapping => no shared edges
    motifprops[:, 6] = expectations_squared
    # one bottom node overlapping => no shared edges
    motifprops[:, 7] = expectations_squared
    # no overlap => no shared edges
    motifprops[:, 8] = expectations_squared
    
    if second_moment:
        result = motifprops @ partition
    else:
        result = motifprops @ partition - (binom(v0, 2) * binom(v1, 2) * expectations)**2
    
    if array:
        return result
    else:
        return {k : v for k, v in zip(sma.MOTIF4_NAMES, result)}


def distributionMotifsActorsChoice(G : nx.Graph, 
                                   *arities, 
                                   roles = [], 
                                   level : int = -1,
                                   array : bool = False):
    """
    Computes expectation and variances for Actor's Choice distribution of motifs.
    See the documentation for a description of this model.
    
    If ``level = -1``, then the first entry equalling two in the signature of
    the motif is taken as level.
    
    :param G: the SEN
    :param arities: arities of the (multi-level) motif
    :param level: level which is assumed to be variable in the Actor's Choice Model
    :param array: whether the output is a tuple ``(e,v)`` where ``e`` is a vector
        of expectations and ``v`` a vector of variances, or dict mapping motif names
        to tuples of expectation and variance for this motif
    :returns: properties of the distribution as tuple or dict (see ``array``)
    """
    signature  = sma.multiSignature(arities)
    motif_info = sma.motifInfo(signature, G.is_directed())
    positions  = sma.matchPositions(motif_info.signature, arities, roles)
    
    if level < 0:
        assert 2 in signature, 'signature does not contain two'
        level = positions[motif_info.signature.index(2)]
    
    contributions, _    = sma.edgeContributionList(G, *motif_info.signature, roles = positions, level = level)
    p                   = sma.densityMatrix(G)[level,level]
    sums                = numpy.sum(contributions, axis = 1)
    squares             = numpy.sum(contributions**2, axis = 1)
    expectations_open   = (1-p) * sums
    expectations_closed = p * sums
    variances           = p * (1-p) * squares
    
    # de-group open and closed motifs
    indexer = {motif : i for i, motif in enumerate(motif_info.classes)}
    abstract_level = positions.index(level)
    if abstract_level not in motif_info.projections:
        raise NotImplementedError('ActorsChoice not implemented for signature %s on level %d' \
                                  % (str(motif_info.signature), level))
    grouper = motif_info.projections[abstract_level]
    e = numpy.zeros((len(indexer),))
    v = numpy.zeros((len(indexer),))
    for (op, cl), eo, ec, var in zip(grouper, expectations_open, expectations_closed, variances):
        e[indexer[op]] = eo
        e[indexer[cl]] = ec
        v[indexer[op]] = v[indexer[cl]] = var
    
    if array:
        return (e,v)
    else:
        return {k : (exp, var) for (k, exp, var) in zip(motif_info.classes, e, v)}


# Statistical helper function
def markovBound(value : numpy.ndarray, expectation : numpy.ndarray) -> numpy.ndarray:
    """
    Uses Markov's inequality to compute bounds for the probability that a random
    variable with given expectation takes values higher than the given values.
    
    .. math::
        
        \mathbb{P}[X \geq a] \leq \\frac{\mathbb{E}[X]}{a} 
        
    where :math:`a` is given by ``values`` and :math:`\mathbb{E}[X]` is given
    by ``expectation``.
    
    See `Markov's inequality on Wikipedia <https://en.wikipedia.org/wiki/Markov%27s_inequality>`_.
    
    :param value: the value
    :param expectation: the expectation
    :returns: bounds on the probabilities
    """
    return expectation / value

def cantelliBound(value : numpy.ndarray, 
                  expectation : numpy.ndarray, 
                  variance : numpy.ndarray) -> numpy.ndarray:
    """
    Uses Cantelli's inequality to compute bounds for the probability that a random
    variable with given expectation takes values higher/lower than the given values.
    
    .. math::
        :nowrap:
        
        \[
        \mathbb{P}[X - \mathbb{E}[X]\geq a] \leq 
        \\begin{cases}
        \\frac{\sigma^2}{\sigma^2 + a^2}, & a > 0 \\\\
        1 - \\frac{\sigma^2}{\sigma^2 + a^2}, & a < 0 \\\\ \end{cases}.
        \]
    
    where :math:`a` is given by ``value`` minus ``expectation`` and 
    :math:`\sigma^2` is given by ``variance``.
    
    See `Cantelli's inequality on Wikipedia <https://en.wikipedia.org/wiki/Cantelli%27s_inequality>`_.
    
    :param value: the value
    :param expectation: the expectation
    :returns: bounds on the probabilities
    """
    l = value - expectation
    bound = variance / (variance + l**2)
    signs = l < 0
    return signs * 1 + ((signs * -2)+1) * bound