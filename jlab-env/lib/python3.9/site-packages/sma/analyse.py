# -*- coding: utf-8 -*-

import itertools
import multiprocessing
import numpy
import networkx as nx
import scipy.special
import sma

# Counters
def countMotifs(G : nx.Graph, 
                classificator : sma.MotifClassificator, 
                iterator : sma.MotifIterator, 
                processes : int = 0,
                norm : bool = False,
                array : bool = False,
                chunksize : int = 10000,
                progress_report : bool = False,
                progress_total : int = -1):
    """
    General function for classifying and counting motifs. 
    
    Procedure:
        1. motifs are drawn from the iterator
        2. classificator is called for every motif
        3. the number of occurrences is computed for every class defined in classes
    
    Note, that this function provides for must cases to many options. See
    :py:meth:`sma.count4Motifs`, :py:meth:`sma.count3EMotifs` and :py:meth:`sma.count3SMotifs`.
    
    This function supports multiprocessing. Set processes to any value other than zero
    to use several processes to solve the task. Set processes to None to use 
    :py:class:`multiprocessing.pool.Pool`'s default value.
    
    Set norm to True to get normalized counts, i.e. in this case the sum of all counts
    equals one.
    
    Set array to True to get an array where the indices match with the indices of the classes
    in classes instead of a dict mapping classes to their respective counts.
    
    :param G: the graph
    :param classificator: a :py:class:`sma.MotifClassificator` for classifying the
        motifs
    :param iterator: an iterator yielding motifs. Note, that the format of the motifs must be
        somehow compatible with the format used by the classificator. See :py:func:`sma.iterate4Motifs` etc.
    :param processes: number of processes the task is split among for multiprocessing. Set processes to zero
        to disable multiprocessing.
    :param chunksize: in multiprocessing mode size of each chunk that is sent to
        a child
    :param norm: whether the counts should be normalized in the way that they sum up to one.
    :param array: whether the results should be returned as array (indices map the indices in classes) or
        as dict mapping a class to its count
    :param progress_report: whether a progress report should be printed
    :param progress_total: total number of motifs to count for progress report
    :returns: number of occurrences of the specified classes in either an array or a dict, cf. parameter array

    """
    classes = classificator.info().classes
    result = {key : 0 for key in classes}
    
    if progress_total < 0:
        progress_report = False
        
    if processes <= 1:
        classified = map(classificator, iterator)
        if progress_report:
            classified = sma.progress_indicator(classified, progress_total)
        for cl in classified:
            result[cl] += 1
            del cl
    else:
        with multiprocessing.Pool(processes) as p:
            classified = p.imap_unordered(classificator, 
                                          iterator, 
                                          chunksize = chunksize)
            if progress_report:
                classified = sma.progress_indicator(classified, 
                                                    progress_total)
            for cl in classified:
                result[cl] += 1
                del cl
            p.close()
            p.join()
    
    # normalize
    if norm:
        factor = 1. / sum(result.values())
        result = {key : factor * result[key] for key in result}

    # output format    
    if array:
        return numpy.array([result[k] for k in classes])
    
    return result

def count4Motifs(G : nx.Graph, 
                 level0 = sma.NODE_TYPE_SOC, 
                 level1 = sma.NODE_TYPE_ECO, 
                 **kwargs):
    """
    Front-end function for counting 4-motifs in a given graph.
    If iterator is None (default) :py:meth:`sma.iterate4Motifs` is used.
    
    See :py:meth:`sma.countMotifs` for details. See also :py:meth:`sma.count4MotifsSparse`.
    
    :param G: the graph
    :param level0: sesType of the lower level
    :param level1: sesType of the upper level
    :param kwargs: additional parameters for :py:meth:`sma.countMotifs`
    """
    iterator = iterate4Motifs(G, level0, level1)
    return countMotifs(G, 
                       sma.FourMotifClassificator(G), 
                       iterator, 
                       progress_total = sma.totalMultiMotifs(G, *sma.sortPositions([level0, level1], [2,2])),
                       **kwargs)

def count3Motifs(G : nx.Graph, level0, level1, **kwargs):
    """
    Front-end function for counting 3-motifs in a given graph.
    
    See :py:meth:`sma.countMotifs` for details. See also :py:meth:`sma.count3MotifsSparse`.
    
    :param G: the graph
    :param level0: sesType of the lower level
    :param level1: sesType of the upper level
    :param kwargs: additional parameters for :py:meth:`sma.countMotifs`
    """
    iterator = iterate3Motifs(G, level0, level1)
    return countMotifs(G, 
                       sma.ThreeMotifClassificator(G), 
                       iterator, 
                       progress_total = sma.totalMultiMotifs(G, *sma.sortPositions([level0, level1], [1,2])),
                       **kwargs)

def count3EMotifs(G : nx.Graph, iterator = None, **kwargs):
    """
    Front-end function for counting 3E-motifs (distinct ecological node) in a given graph.
    If iterator is None (default) :py:meth:`sma.iterate3EMotifs` is used.
    
    See :py:meth:`sma.countMotifs` for details. See also :py:meth:`sma.count3MotifsSparse`.
    
    :param G: the graph
    :param iterator: a custom iterator, if None (default) :py:meth:`sma.iterate3EMotifs` is used.
    :param kwargs: additional parameters for :py:meth:`sma.countMotifs`
    
    """
    if iterator is None:
        iterator = iterate3EMotifs(G)
    return countMotifs(G, 
                       sma.ThreeMotifClassificator(G), 
                       iterator, 
                       progress_total = sma.total3EMotifs(G),
                       **kwargs)

def count3SMotifs(G : nx.Graph, iterator = None, **kwargs):
    """
    Front-end function for counting 3S-motifs (distinct social node) in a given graph.
    If iterator is None (default) :py:meth:`sma.iterate3SMotifs` is used.
    
    See :py:meth:`sma.countMotifs` for details. See also :py:meth:`sma.count3MotifsSparse`.
    
    :param G: the graph
    :param iterator: a custom iterator, if None (default) :py:meth:`sma.iterate3SMotifs` is used.
    :param kwargs: additional parameters for :py:meth:`sma.countMotifs`
    """    
    if iterator is None:
        iterator = iterate3SMotifs(G)
    return countMotifs(G, 
                       sma.ThreeMotifClassificator(G), 
                       iterator, 
                       progress_total = sma.total3SMotifs(G),
                       **kwargs)

def count3MotifsSparse(G : nx.Graph, 
                       level0, 
                       level1, 
                       array : bool = False,
                       progress_report : bool = False):
    """
    Alternative function for counting 3-motifs optimised for sparse SENs, i.e.
    networks with :math:`|E| \ll |V|^2` for :math:`|E|` number of edges, :math:`V`
    number of vertices.
    
    This function counts 3-motifs with an asymptotic execution time of :math:`O(|E||V|)`.
    Multilevel networks are supported. Use parameters ``level0`` (resp. ``level1``)
    to specify the ``sesType`` of the distinct node (resp. the other nodes).
    
    The performance improvement is achieved by iterating over all cross-level edges 
    and in an inner loop over all vertices in ``level1`` distinct from the node 
    contained in the edge. Then the following arithmetic steps are performed:
        
        - the number of I.C and II.C motifs is halved since they are counted twice
          due to their symmetry
        - the total number of edges that have been already encountered in the loop
          described above is computed. Here :py:const:`sma.MOTIF3_EDGES` is used.
        - it remains only to adjust the number of I.A (no edges at all) and of I.C
          (one edge in ``level1`` only) motifs. The number of I.C motifs is the difference
          of the total number of ``level1``-``level1`` edges counted with multiplicity
          and the number of already encountered edges of this type
        - the number of I.A motifs is the total number of 3-motifs, cf. :py:meth:`totalMultiMotifs`,
          and the amount of motifs already encountered
    
    The penultimate step is based on the following observation: There are six different
    classes of 3-motifs. Let :math:`m \in \mathbb{N}^6` be a row vector denoting the numbers of
    occurences of the motif classes. Let :math:`C \in \mathbb{N}^{6 \\times 2}` denote 
    the matrix in :py:const:`sma.MOTIF3_EDGES` containing one row for every motif
    class with two entries each. The first entry represents the number of ``level1``
    edged contained in this motif, the second the number of ``level0`` edges. Let
    :math:`V_i` denote the set of vertices in level :math:`i`, :math:`E_{i,j}` the 
    set of edges from level :math:`i` to level :math:`j`. Then we have the following
    equalities
    
    .. math ::
        
        (m C)_{0} = |V_0| |E_{1,1}|, \quad 
        (m C)_{1} = (|V_1| - 1) |E_{0,1}|.
    
    Both follow using a double counting principle.
    
    Warning: The input graph must not contain self loops. Check using 
    :py:meth:`networkx.nodes_with_selfloops`.
    
    See also :py:meth:`sma.count3Motifs`.
    
    :param G: the SEN
    :param level0: ``sesType`` of the distinct node
    :param level1: ``sesType`` of the other nodes
    :param array: whether the output should be an array or a dict
    :param progress_report: whether a progress report should be printed
    :returns: array or dict with numbers of 3-motifs
    """
    result = {key : 0 for key in sma.MOTIF3_NAMES}
    
    H = G.subgraph(filter(lambda x : G.nodes[x]['sesType'] == level0 or G.nodes[x]['sesType'] == level1, G.nodes))
    data = H.nodes(data=True)
    
    edges_count11 = 0
    edges_count01 = 0
    
    edges = H.edges()
    if progress_report:
        edges = sma.progress_indicator(edges, 
                                       total = H.number_of_edges(),
                                       msg = 'Classifying {:,} gadgets')
    for edge in edges:
        v1, v2 = edge
        if data[v1]['sesType'] != data[v2]['sesType']:
            edges_count01 += 1
            e1 = v1 if data[v1]['sesType'] == level1 else v2
            s  = v1 if data[v1]['sesType'] == level0 else v2
            for e2 in sma.sesSubgraph(H, level1):
                if e1 != e2:
                    result[sma.classify3Motif(G, (s, e1, e2))] += 1
        elif data[v1]['sesType'] == level1 and data[v2]['sesType'] == level1:
             edges_count11 += 1
    # remove symmetry
    result['I.C'] //= 2
    result['II.C'] //= 2

    result_array = numpy.array([result[key] for key in sma.MOTIF3_NAMES])
    counts = result_array @ sma.MOTIF3_EDGES
    V = sma.nodesCount(H)
    
    result_array[3] = V[level0] * edges_count11 - counts[0]
    result_array[0] = V[level0] * V[level1] * (V[level1] - 1) // 2 - sum(result_array)
    
    if not array:
        return {k : v for k, v in zip(sma.MOTIF3_NAMES, result_array)}
    return result_array

def count3SMotifsSparse(G : nx.Graph, **kwargs):
    """
    Wrapper for :py:meth:`sma.count3MotifsSparse`.
    :param G: the SEN
    :param kwargs: optional arguments for :py:meth:`sma.count3MotifsSparse`.
    """
    return count3MotifsSparse(G, sma.NODE_TYPE_SOC, sma.NODE_TYPE_ECO, **kwargs)
def count3EMotifsSparse(G : nx.Graph, **kwargs):
    """
    Wrapper for :py:meth:`sma.count3MotifsSparse`.
    :param G: the SEN
    :param kwargs: optional arguments for :py:meth:`sma.count3MotifsSparse`.
    """
    return count3MotifsSparse(G, sma.NODE_TYPE_ECO, sma.NODE_TYPE_SOC, **kwargs)

def count4MotifsSparse(G : nx.Graph, 
                       level0 = sma.NODE_TYPE_SOC, 
                       level1 = sma.NODE_TYPE_ECO, 
                       guess_IV_A : int = -1, 
                       array : bool = False,
                       progress_report : bool = False):
    """
    Alternative function for counting 4-motifs optimised for sparse SENs, i.e.
    networks with :math:`|E| \ll |V|^2` for :math:`|E|` number of edges, :math:`V`
    number of vertices.
    
    This function counts 4-motifs with an asymptotic execution time of :math:`O(|E||V|^2)`.
    Multilevel networks are supported. Use parameters ``level0`` (resp. ``level1``)
    to specify the ``sesType`` of the upper level (resp. the lower level) or keep
    the default values to count classical 4-motifs, i.e. as counted by 
    :py:meth:`sma.count4Motifs`.
    
    See :py:meth:`sma.count3MotifsSparse` for a more detailed description of the
    procedure.
    
    **Computing the numbers of motifs IV.A-IV.D:** This function iterates over
    cross-level edges (and in an inner loop over one node from each of the two levels). 
    This means that motifs without cross-level edges (IV.A to IV.D) cannot be recognised.
    However the number of these motifs can be reconstructed based on the numbers
    for the other motifs. After completing the iteration we know the numbers of 
    all motifs except for the classes IV.A to IV.D. Based on the double counting 
    formulas outlined in :py:meth:`sma.count3MotifsSparse` we can compute the number
    of edges :math:`E_i` in level :math:`i` that we have not encountered yet. 
    The number of remaining motifs :math:`M` can be easily computed as well 
    following :py:meth:`sma.total4Motifs`. Then the following linear equations hold.

    .. math ::
        
        \\text{IV.B} + \\text{IV.D} &= E_0  \\\\
        \\text{IV.C} + \\text{IV.D} &= E_1  \\\\
        \\text{IV.A} + \\text{IV.B} + \\text{IV.C} + \\text{IV.D} &= M \\ 
    
    Unfortunately, this system of linear equation does not admit a unique solution.
    However, if the number of IV.A motifs is known (specified using parameter
    ``guess_IV_A``), then the system can be easily solved by setting
    :math:`M' = M - \\mathtt{guess\\_IV\\_A}` and computing

    .. math ::
        
        \\left(\\begin{matrix}\\text{IV.B}\\\\\\text{IV.C}\\\\\\text{IV.D}\\end{matrix}\\right)
        =
        \\left(\\begin{matrix}1&0&1\\\\0&1&1\\\\1&1&1\\end{matrix}\\right)^{-1}
        \\left(\\begin{matrix}E_0\\\\E_1\\\\M'\\end{matrix}\\right)
        =
        \\left(\\begin{matrix}0&-1&1\\\\-1&0&1\\\\1&1&-1\\end{matrix}\\right)
        \\left(\\begin{matrix}E_0\\\\E_1\\\\M'\\end{matrix}\\right).
        
    If ``guess_IV_A`` is negative, the values for IV.A-IV.D will be set to :math:`-1`.
    Note that in the case the sum of all returned values does not equal the integer
    returned by :py:meth:`sma.total4Motifs` any more.
    
    See also :py:meth:`sma.count4Motifs`.
    
    :param G: the SEN
    :param level0: ``sesType`` of the lower nodes, social in classical 4-motifs
    :param level1: ``sesType`` of the upper nodes, ecological in classical 4-motifs
    :param guess_IV_A: value for the number of IV.A or something negative if the
        the number of IV.A-IV.D motifs shall not be computed
    :param array: whether the output should be an array or a dict
    :param progress_report: whether a progress report should be printed
    :returns: array or dict with numbers of 4-motifs
    """
    result = {key : 0 for key in sma.MOTIF4_NAMES}
    
    H = G.subgraph(filter(lambda x : G.nodes[x]['sesType'] == level0 or G.nodes[x]['sesType'] == level1, G.nodes))
    data = H.nodes(data=True)
    
    edges_count00 = 0
    edges_count01 = 0
    edges_count11 = 0
    
    classificator = sma.FourMotifClassificator(G)
    edges = H.edges() 
    if progress_report:
        edges = sma.progress_indicator(edges, 
                                       H.number_of_edges(),
                                       msg = 'Classifying {:,} gadgets')
    
    for edge in edges:
        v1, v2 = edge
        if data[v1]['sesType'] != data[v2]['sesType']:
            edges_count01 += 1
            e1 = v1 if data[v1]['sesType'] == level1 else v2
            s1 = v1 if data[v1]['sesType'] == level0 else v2
            classified = map(classificator,  itertools.product([s1],
                                                               filter(lambda s2: s2 != s1, sma.sesSubgraph(G, level0)),
                                                               [e1],
                                                               filter(lambda e2: e2 != e1, sma.sesSubgraph(G, level1))))
            for cl in classified:
                result[cl] += 1
                del cl
        elif data[v1]['sesType'] == level0:
            edges_count00 += 1
        else:
            edges_count11 += 1
            
    result_array  = numpy.array([result[key] for key in sma.MOTIF4_NAMES])
    # remove symmetry
    numpy.floor_divide(result_array, sma.MOTIF4_SYMMETRIES, out = result_array)
    
    if guess_IV_A >= 0: # guess mode
        V = sma.nodesCount(H)
        expected = numpy.array([scipy.special.comb(V[level1], 2, exact = True) * edges_count00,
                                (V[level0]-1)*(V[level1]-1) * edges_count01,
                                scipy.special.comb(V[level0], 2, exact = True) * edges_count11])
        missing = expected - (result_array @ sma.MOTIF4_EDGES)
        totalMotifs = scipy.special.comb(V[level0], 2, exact = True) * scipy.special.comb(V[level1], 2, exact = True)
        n = totalMotifs - sum(result_array) - guess_IV_A
        v = numpy.array([missing[0], missing[2], n])
        A = numpy.array([[0,-1,1],[-1,0,1],[1,1,-1]])
        
        result_array[12] = guess_IV_A
        result_array[13:16] = A @ v
    else:
        result_array[12:16] = [-1] * 4
    
    if not array:
        return {k : v for k, v in zip(sma.MOTIF4_NAMES, result_array)}
    return result_array

def count121MotifsSparse(G : nx.Graph,
                         level0,
                         level1,
                         level2,
                         array : bool = False,
                         optimize_top_adjacent : bool = False,
                         debug_unclassified : bool = False,
                         progress_report : bool = False):
    """
    Counts multi level motifs with arities 1, 2, 1, cf. 
    :py:class:`sma.Multi121MotifClassificator`. This function is faster than
    :py:meth:`sma.countMultiMotifs` for sparse graphs, i.e. graphs with few edges.
    The speed up is achieved by (instead of iterating over all suitable tuples of nodes):
        
        - iterating over all nodes in the lowest level
        - for each of them, iterating over the adjacent nodes in the top level
          (or over all nodes from the top level if ``optimize_top_adjacent = False``)
        - for each of them, iterating over all nodes from the middle level that
          are adjacent to the node in the lowest level
          
    With default parameters, this function counts motifs of all classes correctly.
    If ``optimize_top_adjacent = True``, only classes ``3`` and ``4`` are counted correctly.
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper level
    :param level1: ``sesType`` of the middle level
    :param level2: ``sesType`` of the lower level
    :param array: whether the output should be an array or a dict
    :param optimize_top_adjacent: whether the counting should be optimize for
        counting motifs of classes ``3`` and ``4``, see above.
    :param debug_unclassified: whether, in case that ``optimize_top_adjacent = True``,
        the partial count for class ``-1`` should be returned. Per default, the 
        value is set to a negative value.
    :param progress_report: whether a progress report should be printed
    """
    motif_info = sma.Motif121Info
    classificator = motif_info.classificator(G)
    result = {k : 0 for k in motif_info.classes}
    node_counts = nodesCount(G)
    level2_nodes = sma.sesSubgraph(G, level2)
    if progress_report:
        level2_nodes = sma.progress_indicator(level2_nodes, 
                                              node_counts[level2],
                                              msg = 'Classifying {:,} gadgets')
    for lower in level2_nodes:
        if optimize_top_adjacent:
            top = filter(lambda x: G.nodes[x]['sesType'] == level0, G[lower])
        else:
            top = sma.sesSubgraph(G, level0)
        middle = filter(lambda x: G.nodes[x]['sesType'] == level1, G[lower])
        for a, (b,c) in itertools.product(top,itertools.combinations(middle, 2)):
            cl = classificator((a, b, c, lower))
            result[cl] +=1
            del cl
    if optimize_top_adjacent:
        result[1] = result[2] = -1 # set to implausible value
        if not(debug_unclassified):
            result[-1] = -1
    else:
        total = node_counts[level0] *\
                scipy.special.comb(node_counts[level1], 2, exact = True) *\
                node_counts[level2]
        result[-1] = total - sum(result.values()) + result[-1]
    if array:
        return numpy.fromiter(result.values(), dtype=int)
    return result

def count221MotifsSparse(G : nx.Graph,
                         level0,
                         level1,
                         level2,
                         array : bool = False,
                         optimize_top_adjacent : bool = False,
                         debug_unclassified : bool = False,
                         **kwargs):
    """
    Counts multi level motifs with arities 2, 2, 1, cf. 
    :py:class:`sma.Multi221MotifClassificator`. This function is faster than
    :py:meth:`sma.countMultiMotifs` for sparse graphs, i.e. graphs with few edges.
    The speed up is achieved by (instead of iterating over all suitable tuples of nodes):
        
        - iterating over all nodes in the lower level
        - for each of them iterating over all pairs of combinations of two nodes
          from the top level, and
        - two nodes from the middle level adjacent to the lower level node.
    
    If ``optimize_top_adjacent = True``, this function iterates only over top level
    nodes which are adjacent to the lower level node. In this case only motifs of
    classes *CLASS*.3 are counted correctly. 
    
    With default parameters, only motifs of classes *CLASS*.2 and *CLASS*.3 are counted
    correctly. The values for ``Unclassified``, *CLASS*.1, *CLASS*.0 will be set 
    to a negative value.
    
    This function supports multiprocessing.
    
    See also :py:class:`sma.DenseMulti221Motifs`, the motif source used here for speed-up.
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper level
    :param level1: ``sesType`` of the middle level
    :param level2: ``sesType`` of the lower level
    :param array: whether the output should be an array or a dict
    :param optimize_top_adjacent: whether the counting should be optimize for
        counting motifs of classes *CLASS*.3, see above.
    :param processes: number of processes for multiprocessing
    :param chunksize: chunksize for multiprocessing
    :param debug_unclassified: whether, the partial count for class ``Unclassified``
        should be returned. Per default, the value is set to a negative value.
    :param kwargs: further parameters for :py:meth:`sma.countMotifs`
    """
    classificator = sma.Multi221MotifClassificator(G)
    iterator = sma.DenseMulti221Motifs(G, level0, level1, level2, optimize_top_adjacent)
    result = countMotifs(G, 
                         classificator, 
                         iterator,
                         **kwargs)
    
    # mark implausible results
    if not(debug_unclassified):
        result['Unclassified'] = -1
    implausible = [0,1]
    if optimize_top_adjacent:
        implausible = implausible + [2]
    for v in itertools.product(sma.MOTIF4_NAMES, implausible):
        result['{}.{}'.format(*v)] = -1
        
    # convert to array?
    if array:
        return numpy.fromiter(result.values(), dtype=int)
    return result

def count13MotifsSparse(G : nx.Graph,
                         level0,
                         level1,
                         array : bool = False,
                         **kwargs):
    """
    Counts multi level motifs with arities 1, 3 cf. 
    :py:class:`sma.OneThreeMotifClassificator`. This function is faster than
    :py:meth:`sma.countMultiMotifs` for sparse graphs, i.e. graphs with few edges.
    
    This function supports multiprocessing.
    
    See also :py:class:`sma.Dense13Motifs`, the motif source used here for speed-up.
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper level
    :param level1: ``sesType`` of the middle level
    :param array: whether the output should be an array or a dict
    :param processes: number of processes for multiprocessing
    :param chunksize: chunksize for multiprocessing
    :param debug_unclassified: whether, the partial count for class ``Unclassified``
        should be returned. Per default, the value is set to a negative value.
    :param kwargs: further parameters for :py:meth:`sma.countMotifs`
    """
    classificator = sma.OneThreeMotifClassificator(G)
    iterator = sma.Dense13Motifs(G, level0, level1)
    result = countMotifs(G, 
                         classificator, 
                         iterator,
                         **kwargs)
    # convert to array?
    if array:
        return numpy.fromiter(result.values(), dtype=int)
    return result

class _count222MotifsSparseCounter:
    def __init__(self, G, level0, level1, level2):
        self.G = G
        self.level0 = level0
        self.level1 = level1
        self.level2 = level2
    def __call__(self, lower_edge):
        result = [0] * 3
        lower1, lower2 = lower_edge
        middle_neighbours = set(sma.sesSubgraph(self.G, self.level1, self.G[lower1]))
        top_neighbours    = set(sma.sesSubgraph(self.G, self.level0, self.G[lower1]))
        middles           = middle_neighbours.intersection(set(sma.sesSubgraph(self.G, self.level1, self.G[lower2])))
        tops              = top_neighbours.intersection(set(sma.sesSubgraph(self.G, self.level0, self.G[lower2])))
        for m, t in itertools.product(itertools.combinations(middles, 2), 
                                      itertools.combinations(tops, 2)):
            if (not(self.G.has_edge(*m)) and 
                self.G.has_edge(m[0], t[0]) and
                self.G.has_edge(m[0], t[1]) and
                self.G.has_edge(m[1], t[0]) and
                self.G.has_edge(m[1], t[1])):
                if self.G.has_edge(*t):
                    result[2] += 1
                else:
                    result[1] += 1
            else:
                result[0] += 1
        return result
def count222MotifsSparse(G : nx.Graph,
                         level0,
                         level1, 
                         level2,
                         array : bool = False,
                         processes : int = 0,
                         chunksize : int = 5,
                         debug_unclassified : bool = False,
                         progress_report : bool = False):
    """
    Counts multi level motifs with arities 2, 2, 2, cf. 
    :py:class:`sma.Multi222MotifClassificator`. This function is faster than
    :py:meth:`sma.countMultiMotifs` for sparse graphs, i.e. graphs with few edges.
    The speed up is achieved by (instead of iterating over all suitable tuples of nodes):
        
        - iterating over all edges between two lower level nodes
        - for each of them, iterating over all middle level nodes which are simultaneously
          neighbours of both ends of the edge and over all top level nodes which
          are simultaneously neighbours of both ends of the edge
    
    This function counts only motifs of classes ``3`` and ``4`` correctly. All other
    counts are set to a negative value.
    
    This function supports multiprocessing. Relatively small chunksizes are 
    recommended.
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper level
    :param level1: ``sesType`` of the middle level
    :param level2: ``sesType`` of the lower level
    :param array: whether the output should be an array or a dict
    :param processes: number of processes for multiprocessing
    :param chunksize: chunksize for multiprocessing
    :param debug_unclassified: whether, the partial count for class ``-1``
        should be returned. Per default, the value is set to a negative value.
    :param progress_report: whether a progress report should be printed
    """
    result = numpy.zeros((3,), dtype=int)
    lowerlevel = G.subgraph(sma.sesSubgraph(G, level2))
    if processes > 1:
        with multiprocessing.Pool(processes) as p:
            classified = p.imap_unordered(_count222MotifsSparseCounter(G, level0, level1, level2), 
                                          lowerlevel.edges(), chunksize = chunksize)
            if progress_report:
                classified = sma.progress_indicator(classified, 
                                                    lowerlevel.number_of_edges(),
                                                    msg = 'Classifying {:,} gadgets')
            for cl in classified:
                result = result + numpy.array(cl)
                del cl
            p.close()
            p.join() 
    else:
        classified = map(_count222MotifsSparseCounter(G, level0, level1, level2), lowerlevel.edges())
        if progress_report:
            classified = sma.progress_indicator(classified, 
                                                lowerlevel.number_of_edges(),
                                                msg = 'Classifying {:,} gadgets')
        for cl in classified:
            result = result + numpy.array(cl)
            del cl
    real_result = [result[0], -1, -1, result[1], result[2]]
    if not(debug_unclassified):
        real_result[0] = -1
    if not(array):
        return {k : v for k, v in zip([-1, 1, 2, 3, 4], real_result)}
    return numpy.array(real_result)

# Iterators
    
def iterate4Motifs(G : nx.Graph, 
                   level0 = sma.NODE_TYPE_SOC, 
                   level1 = sma.NODE_TYPE_ECO):
    """
    Yields all tuples (s1,s2,e1,e2) where s1,s2 are social nodes,
    e1,e2 are ecological nodes
    
    The tuples are not distinct w.r.t. their order, i.e. (1,2) = (2,1).
    The internal order of :py:meth:`sma.sesSubgraph` is kept. 
    
    :param G: the graph
    :param level0: ``sesType`` of the upper nodes, usually :py:const:`sma.NODE_TYPE_SOC`
    :param level1: ``sesType`` of the lower nodes, usually :py:const:`sma.NODE_TYPE_ECO`
    """
    socialSubgraph = sesSubgraph(G, level0)
    ecologicalSubgraph = sesSubgraph(G, level1)
    return itertools.starmap(lambda x,y: (*x,*y),itertools.product(
            itertools.combinations(socialSubgraph, 2),
            itertools.combinations(ecologicalSubgraph, 2)))

def iterate3Motifs(G : nx.Graph, level0, level1):
    """
    Yields all tuples (a, b1, b2) where a is a node from ``level0`` and b1, b2 
    nodes from ``level1``. This is a back-end function for :py:meth:`sma.iterate3EMotifs`
    and :py:meth:`sma.iterate3SMotifs`.
    
    :param G: the graph
    :param level0: ``sesType`` of the distinct node, e.g. in 3E-motifs :py:const:`sma.NODE_TYPE_ECO`
    :param level1: ``sesType`` of the other nodes, e.g. in 3E-motifs :py:const:`sma.NODE_TYPE_SOC`
    """
    ecologicalSubgraph = sesSubgraph(G, level0)
    socialSubgraph = sesSubgraph(G, level1)
    return map(lambda x: (x[0],*x[1]), 
               itertools.product(ecologicalSubgraph, 
                                 itertools.combinations(socialSubgraph, 2)))

def iterate3EMotifs(G : nx.Graph,
                    level0 = sma.NODE_TYPE_ECO,
                    level1 = sma.NODE_TYPE_SOC):
    """
    Yields all tuples (e, s1, s2) where e is an ecological node and
    s1,s2 are social nodes.
    
    The tuples are not distinct w.r.t. their order, i.e. (1,2) = (2,1).
    The internal order of :py:meth:`sma.sesSubgraph` is kept.
    
    See also :py:meth:`sma.iterate3Motifs`.
    
    :param G: the graph
    :param level0: ``sesType`` of the distinct node, here :py:const:`sma.NODE_TYPE_ECO`
    :param level1: ``sesType`` of the other nodes, here :py:const:`sma.NODE_TYPE_SOC`
    """
    return iterate3Motifs(G, level0, level1)

def iterate3SMotifs(G : nx.Graph,
                    level0 = sma.NODE_TYPE_SOC,
                    level1 = sma.NODE_TYPE_ECO):
    """
    Yields all tuples (s, e1, e2) where s is a social node and 
    e1, e2 are ecological nodes.
    
    The tuples are not distinct w.r.t. their order, i.e. (1,2) = (2,1).
    The internal order of :py:meth:`sma.sesSubgraph` is kept.
    
    See also :py:meth:`sma.iterate3Motifs`.
    
    :param G: the graph
    :param level0: ``sesType`` of the distinct node, here :py:const:`sma.NODE_TYPE_SOC`
    :param level1: ``sesType`` of the other nodes, here :py:const:`sma.NODE_TYPE_ECO`
    """
    return iterate3Motifs(G, level0, level1)

def sesSubgraph(G : nx.Graph, sesType : int, source = None) -> filter:
    """
    Filters only social or ecological nodes from a given graph. The returned 
    object is a filter. If you need a :py:class:`networkx.Graph`, you may want
    to call ``G.subgraph`` on the result.
    
    .. code :: Python
    
        # Let G be some SEN
        socialNodes = list(sma.sesSubgraph(G, sma.NODE_TYPE_SOC))
        socialGraph = G.subgraph(sma.sesSubgraph(G, sma.NODE_TYPE_SOC))
    
    :param G: the graph
    :param sesType: the type (either social or ecological), see
        :py:const:`sma.NODE_TYPE_ECO` and :py:const:`sma.NODE_TYPE_SOC`.
    :param source: an alternative source for nodes, if ``None``, ``G.nodes`` is used
    :returns: filter object with yields the nodes. Be aware that you will need to 
        call :py:func:`list` on the result to obtain a list.
    """
    if source == None:
        source = G.nodes
    return filter(lambda x : G.nodes[x]['sesType'] == sesType, source)

# Simple properties

def density(G : nx.Graph) -> float:
    """
    Returns the density of a given graph G = (V, E) defined as 
    
    .. math ::
        
        \\frac{2 |E|}{|V| (|V|-1)}.
    
    See also :py:meth:`sma.densityMatrix`.
    
    :param G: the SEN
    """
    E = G.number_of_edges()
    V = G.number_of_nodes()
    return 2 * E / V / (V-1)

def densityMatrix(G : nx.Graph) -> numpy.ndarray:
    """
    Returns an upper triangular matrix with edge densities for every subsystem, 
    i.e. the entry-wise quotient of 
    :py:meth:`sma.edgesCountMatrix` and :py:meth:`sma.maxEdgeCountMatrix`.
    
    See also :py:meth:`sma.density`.
    
    :param G: the SEN
    """
    v = sma.edgesCountMatrix(G)
    m = sma.maxEdgeCountMatrix(sma.nodesCount(G, array=True))
    return numpy.divide(v, m, where = (m!=0))

def nodesCount(G : nx.Graph, array : bool = False, levels : list = None) -> numpy.ndarray:
    """
    Returns either a dict or an array with the number of nodes in each ``sesType``.
    
    :param G: the SEN
    :param array: whether the result is an array or a dict
    :param levels: a list of levels to provide an empty result if the graph is
        empty
    :raises ValueError: if the graph is empty and ``levels`` is ``None`` or
        if one or more nodes have no nodal attribute ``sesType``.
    """
    if G.number_of_nodes() == 0 and levels is None:
        raise ValueError('cannot give sma.nodesCount for empty graph without explicit levels')
    
    if levels is None:
        levels = sma.sesTypes(G)
    
    levels = sorted(list(levels))
    result = {l : 0 for l in levels}
    
    for n, l in G.nodes(data='sesType'):
        if l is None:
            raise ValueError('the node %s has no sesType' % str(n))
        result[l] += 1
    
    if array:
        return [result[l] for l in levels]
    else:
        return result

def untypedNodes(G : nx.Graph) -> map:
    """
    Returns a map object yielding all nodes which do not have a ``sesType``-attribute.
    Most functions used in analyses require all nodes to have such an attribute.
    
    Example: List all untyped nodes:
    
    .. code :: Python
    
        # Let G be a SEN
        print(list(sma.untypedNodes(G)))
    
    :param G: the SEN
    :returns: map object yielding all untyped nodes    
    """
    return map(lambda v : v[0],
               filter(lambda v : v[1] is None, 
                      dict(G.nodes(data='sesType')).items()))

def edgesCount(G : nx.Graph, array : bool =False) -> dict:
    """
    Classifies all edges in a SEN according to the following classes.
    
        - :py:const:`sma.EDGE_TYPE_SOC_SOC` for edges linking two social nodes
        - :py:const:`sma.EDGE_TYPE_ECO_ECO` for edges linking two ecological nodes
        - :py:const:`sma.EDGE_TYPE_ECO_SOC` for edges linking a social and an ecological node
    
    Since edges are undirected no other types occur. 
    
    See :py:meth:`sma.edgesCountMatrix` for multi-level support.
    
    :param G: SEN as networkx graph
    :param array: whether the result is an array or a dict
    :returns: dict containing type-count pairs according to the list of types above
    """
    def _classify(edge):
        v1, v2 = edge
        types = [G.nodes[v1]['sesType'], G.nodes[v2]['sesType']]
        if types == [sma.NODE_TYPE_SOC, sma.NODE_TYPE_SOC]:
            return sma.EDGE_TYPE_SOC_SOC
        if types == [sma.NODE_TYPE_ECO, sma.NODE_TYPE_ECO]:
            return sma.EDGE_TYPE_ECO_ECO
        if sma.NODE_TYPE_ECO in types and sma.NODE_TYPE_SOC in types:
            return sma.EDGE_TYPE_ECO_SOC
        raise TypeError('sma.edgesCount supports only two-level networks, use sma.edgesCountMatrix instead')
    classification = list(map(_classify, G.edges))
    types, counts = numpy.unique(classification, return_counts=True)
    if array:
        return [int(counts[types == k][0]) if k in types else 0 for k in [sma.EDGE_TYPE_SOC_SOC, sma.EDGE_TYPE_ECO_SOC, sma.EDGE_TYPE_ECO_ECO] ]
    else:
        return { k : int(counts[types == k][0]) if k in types else 0 for k in [sma.EDGE_TYPE_SOC_SOC, sma.EDGE_TYPE_ECO_SOC, sma.EDGE_TYPE_ECO_ECO] }

def edgesCountMatrix(G : nx.Graph, nTypes : int = None) -> numpy.ndarray:
    """
    This function provides an analogous result as :py:meth:`sma.edgesCount` for
    multi-level graphs. For a SEN with :math:`n` types of nodes the returned matrix
    is upper-triangular and of dimension :math:`n \\times n`. The entry :math:`(i,j)`
    contains the number of edges in the given graph linking nodes of type :math:`i`
    and :math:`j`.

    The sum over all entries equals the total number of edges in the SEN.

    The returned matrix can be used as a parameter for :py:meth:`sma.randomMultiSENs`.

    :param G: a SEN, possibly with more than two levels
    :param nTypes: the number of types in the SEN. An ordinary social-ecological network
        has two levels. If ``None``, the number of levels is determined automatically
        using :py:meth:`sma.sesTypes`.
    """
    if nTypes is None:
        nTypes = max(sma.sesTypes(G)) + 1
    res = numpy.zeros((nTypes, nTypes), dtype=int)
    for v1, v2 in G.edges:
        res[G.nodes[v1]['sesType'], G.nodes[v2]['sesType']]+=1
    return numpy.triu(res + res.T) - numpy.diag(numpy.diag(res))

def adjacentEdgesCount(G : nx.Graph, node, nTypes = 2) -> numpy.ndarray:
    """
    The :math:`i`-th entry in the returned matrix row is the number of neighbours
    the given node has of the type :math:`i`. For example, in a ordinary two-level
    SEN with social and ecological nodes the first entry contains the number of 
    adjacent ecological nodes (type 0) whereas the second entry contains the number
    of social nodes (type 1). Multi-level SENs are supported.
    
    :param G: the SEN
    :param node: the node
    :param nTypes: number of types in the SEN, usually 2 (social and ecological)
    :returns: matrix row with numbers of adjacent vertices by type
    """
    neighbors = G[node]
    classification = list(map(lambda n : G.nodes[n]['sesType'], neighbors))
    types, counts = numpy.unique(classification, return_counts = True)
    return numpy.array([counts[types == i][0] if i in types else 0 for i in range(nTypes)], dtype=int)

def total4Motifs(G : nx.Graph) -> int:
    """
    Returns the total number of 4-motifs in a graph, i.e.
    
    .. math ::
        
        {n_s \\choose 2} {n_e \\choose 2} = \\frac{n_s(n_s-1)n_e(n_e-1)}{4}
        
    where n_s and n_e are respectively the numbers of social and ecological nodes.
    
    See also :py:meth:`sma.totalMultiMotifs`.
    
    :param G: the graph
    :returns: total number of 4-motifs
    """
    return totalMultiMotifs(G, 2, 2)

def total3EMotifs(G : nx.Graph) -> int:
    """
    Returns the total number of 3E-motifs in a graph, i.e.
    
    .. math ::
        
        {n_s \\choose 2} n_e = \\frac{n_s(n_s-1)n_e}{2}
        
    where n_s and n_e are respectively the numbers of social and ecological nodes.
    
    See also :py:meth:`sma.totalMultiMotifs`.
    
    :param G: the graph
    :returns: total number of 3E-motifs
    """
    return totalMultiMotifs(G, 1, 2)

def total3SMotifs(G : nx.Graph) -> int:
    """
    Returns the total number of 3S-motifs in a graph, i.e.
    
    .. math ::
        
        {n_e \\choose 2} n_s = \\frac{n_e(n_e-1)n_s}{2}
        
    where n_s and n_e are respectively the numbers of social and ecological nodes.
    
    See also :py:meth:`sma.totalMultiMotifs`.
    
    :param G: the graph
    :returns: total number of 3S-motifs
    """
    return totalMultiMotifs(G, 2, 1)

def totalMultiMotifs(G : nx.Graph, *arities : int) -> int:
    """
    Returns the total number of multilevel motifs of given arities (number of
    nodes taken from each level) for the given graph. If the given arities are
    :math:`a_1, \dots, a_n`, then the returned value is
    
    .. math ::
        
        \prod_{i=1}^n \\binom{N_i}{a_i}
        
    where :math:`N_1, \dots, N_n` are the amounts of vertices in the different levels.
    
    The following function calls are equivalent, cf. :py:meth:`sma.total4Motifs`
    but also :py:meth:`sma.total3EMotifs` and :py:meth:`sma.total3SMotifs`:
        
    .. code :: Python
        
        sma.total4Motifs(G, multi = True)
        # and
        sma.totalMultiMotifs(G, 2, 2)
    
    :param G: the SEN
    :param arities: the arities, i.e. number of nodes taken from each level
    """
    total = 1
    nodes_counts = nodesCount(G)
    for level, arity in enumerate(arities):
        if arity >= 1:
            if level not in nodes_counts or nodes_counts[level] == 0: 
                return 0
            total *= scipy.special.comb(nodes_counts[level], arity, exact = True)
    return total

def sesTypes(G : nx.Graph) -> set:
    """
    Returns the set of all ``sesTypes`` occurring in the given graph.
    
    :param G: the SEN
    :returns: set of all ``sesTypes``, e.g. :math:`\{0, 1\}` in standard two-level
        SENs
    """
    return set(map(lambda k : k[1]['sesType'], G.nodes.data(data=True)))

def degreeDistribution(G : nx.Graph) -> dict:
    """
    Returns a dict mapping each node of the given network to a dict as returned
    by :py:meth:`sma.nodesCount` giving the number of neighbours on the various
    levels.
    
    :param G: the SEN
    :returns: dict of dicts
    """
    levels = sma.sesTypes(G)
    return {node : sma.nodesCount(G.subgraph(G[node]), levels = levels) for node in G.nodes}

def nodesByType(G : nx.Graph) -> dict:
    """
    Returns a dict mapping the levels of the network to list of nodes on the
    respective level.
    
    :param G: the SEN
    :returns: dict of node names by level
    """
    result = {}
    for node, level in G.nodes(data='sesType'):
        if level in result:
            result[level].append(node)
        else:
            result[level] = [node]
    return result