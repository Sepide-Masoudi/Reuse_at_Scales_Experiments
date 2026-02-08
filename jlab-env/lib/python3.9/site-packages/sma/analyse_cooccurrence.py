#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import networkx as nx
import itertools, numpy
import sma
import multiprocessing
import operator

def cooccurrenceTable(G : nx.Graph, *motifs, to_array : bool = False, to_dict : bool = False):
    """
    Returns the co-occurrence table for a given set of motif generators. This table
    contains one row for each node in the given SEN G. The :math:`i`-th entry for 
    the :math:`j`-th row represents the number of occurrences of the :math:`j`-th 
    node in motifs yielded by the :math:`i`-th motif generator.
    
    For example, one could want to count the number of occurrences of nodes in closed
    and open triangles::
        
        import sma
        # let G be some SEN
        result = sma.cooccurrenceTable(G, 
                                       sma.ThreeEMotifs(G) & sma.is3Class('I.C'), 
                                       sma.ThreeEMotifs(G) & sma.is3Class('II.C'))
    
    Then the first entry for each node contains the number of open triangles 
    (class I.C motif) this node is involved in and the second entry the number of
    closed triangles (class II.C motif). Note, that in this example the involvement
    of a node at any position (not only at the distinct position) counts, cf.
    :py:meth:`sma.triangleCoefficient`.
    
    See also :py:meth:`sma.cooccurrenceTableFull`.
    
    :param G: the SEN
    :param motifs: a list of motif generators, cf. :py:class:`sma.MotifIterator`
    :param to_array: Boolean indicating whether the output should be a numpy
        array, entries for nodes a given in the order returned by the graph
    :param to_dict: Boolean indicating whether the output should be a two-level
        dict. Values can be accessed by ``result[node][motif]`` where motif is 
        the string representation of the motif
    :returns: co-occurrence table as described above
    """
    result = {node : [0]*len(motifs) for node in G.nodes}
    for generator, i in zip(motifs, itertools.count()):
        for motif in generator:
            for node in motif:
                result[node][i] += 1
    if to_array:
        return numpy.array(list(result.values()))
    if to_dict:
        gstrings = list(map(lambda x : x.__str__(), motifs))
        return {node : {gstrings[i] : result[node][i] for i in range(len(motifs))} for node in G.nodes}
    return result

def cooccurrenceTableFull(G : nx.Graph, 
                          iterator : sma.MotifIterator, 
                          classificator : sma.MotifClassificator,
                          to_array : bool = False):
    """
    This function returns a dict/array similar to the result of :py:meth:`sma.cooccurrenceTable`.
    This function should be used when the values for several classes of motifs taken
    from the same source iterator are of interest. For example, if all 3-motifs
    shall be fully classified, :py:meth:`sma.cooccurrenceTableFull` should be 
    preferred over :py:meth:`sma.cooccurrenceTable` since it does not incur any 
    redundant costs.
    
    If the parameter ``to_array`` is set to ``False`` (default), the result is 
    a dictionary which maps vertices to sub-dictionaries mapping motif classes (taken
    from the classificator) to the integer representing the number of occasions this
    vertex occurs in a motif of this class. If ``to_array`` is flipped, the result 
    is converted to a matrix with one row for each vertex and one column for each
    motif class.
    
    The sum of all entries equals the total number of motifs in the iterator
    multiplied by the arity of the classificator.
    
    :param G: a SEN
    :param iterator: a :py:class:`sma.MotifIterator` as source of motifs
    :param classificator: a :py:class:`sma.MotifClassificator` for classifying the
        motifs
    :param to_array: whether the result should be an array or a dict.
    :returns: co-occurrences table featuring values for all classes of motifs
    
    """
    result = {node : {} for node in G.nodes}
    for motif in iterator:
        for node in motif:
            typ = classificator(motif)
            if typ in result[node]:
                result[node][typ] += 1
            else:
                result[node][typ] = 1
    if to_array:
        return numpy.array([[row[motif] if motif in row else 0 for motif in classificator.info().classes] for row in result.values()])
    return result
    
def motifMultigraph(G : nx.Graph, *motifs, attr = 'motif') -> nx.MultiGraph:
    """
    Returns a multigraph of motifs. In this multigraph every node represents motif.
    For example, when the second parameter is ``sma.FourMotif(G)``, then every
    node in the returned graph represents one 4-motif. Each edge connecting two 
    nodes :math:`m_1`, :math:`m_2` represents one node in the original graph that is shared by two
    motifs that :math:`m_1` and :math:`m_2` represent.
    
    Note that the motif multigraph does not contain any loops since each motifs
    shares trivially all its vertices with itself.
    
    A list of motif iterators must be given, cf. :py:class:`sma.MotifIterator`.
    In this way different classes of motifs can be incorporated in one multigraph.
    For example, one could be interested in the adjacence of open triangles with
    distinct social node (social motif I.C) and closed triangles with distinct 
    ecological node (ecological motif II.C). Then these two motif iterators can
    be provided as input, cf. :py:class:`sma.ThreeEMotifs`, :py:class:`sma.ThreeSMotifs`
    and :py:class:`sma.is3Class`.
    
    The multigraph can be converted to a weighted simple graph with edge weights
    corresponding to edge multiplicities in the multigraph using :py:meth:`sma.multiToWeightedGraph`.
    See also :py:meth:`sma.motifWeightedGraph`.
    
    The class of the motifs, i.e. a string representation of the given motif 
    iterators, is stored as nodal attribute.
    
    :param G: a SEN
    :param motifs: one or several instances of :py:class:`sma.MotifIterator`
    :param attr: attribute key for the nodal attribute representing the class
        of the motifs, default ``motif``
    :returns: motif multigraph
    """
    M = nx.MultiGraph()
    for motif in motifs:
        M.add_nodes_from(motif, **{attr : motif.__str__()})
    sesTypes = nx.get_node_attributes(G, 'sesType')
    for m1, m2 in itertools.combinations(M.nodes, 2):
        common = set(m1).intersection(set(m2))
        for n in common:
            M.add_edge(m1, m2, sesType=sesTypes[n], name=n)
    return M

def motifWeightedGraph(G : nx.Graph, *motifs, attr='weight') -> nx.Graph:
    """
    Returns a weighted graph corresponding to the motif multigraph generated 
    by :py:meth:`sma.motifMultigraph`. That two motifs share vertices is not
    encoded by multiple edges but by edge weights.
    
    See :py:meth:`sma.multiToWeightedGraph`, the function that takes care of the
    translation.
    
    :param G: the SEN
    :param motifs: one or several instances of :py:class:`sma.MotifIterator`
    :param attr: the attribute key for the weight attribute, default is ``weight``.
    """
    M = motifMultigraph(G, *motifs)
    return sma.multiToWeightedGraph(M, attr)

def motifClassMatrix(G : nx.Graph, 
                     iterator : sma.MotifIterator, 
                     classificator : sma.MotifClassificator,
                     as_symmetric : bool = False) -> numpy.ndarray:
    """
    In the returned quadratic matrix every column and every row represents a motif
    class, i.e. a class of motif as recorgnized by the given :py:class:`sma.MotifClassificator`.
    For example, in case of 3-motifs the first column and the first row represent
    class 'I.A' motifs whereas the last row / column represents 'II.C' motifs. In
    total, the matrix would be of dimension :math:`6 \\times 6` since there are six
    3-motifs.
    
    The :math:`(i,j)`-th entry represents the number of vertices in the given SEN shared
    by motifs of class :math:`i` and :math:`j`. If a vertex is contained in several class 
    :math:`i` and class :math:`j` motifs, it is counted multiply.
    
    Let :math:`(C_{ij})` denote the returned matrix. Then for the sum of all upper
    triangular entries the following correspondence holds:
    
    .. math ::
        
        \\sum_{i \\geq j} C_{ij} = \\frac12 \\sum_{M_1} \\sum_{M_2 \\neq M_1} 
        \\left| M_1 \\cap M_2 \\right|
        
    where :math:`M_1` and :math:`M_2` are motifs taken from the iterator.
    
    This function computes the desired matrix based on the result of :py:meth:`sma.cooccurrenceTableFull`.
    For every vertex its occurrence in each of the possible classes of motifs is
    counted. Let red, blue and orange be three distinct motif classes. If a vertex occurs 
    :math:`n` times in red motifs, :math:`m_1` times in blue motifs and :math:`m_2`
    times in orange motifs, then it establishes :math:`\\binom{n}{2}` connections
    between red motifs. Hence it contributes this number to the red diagonal entry.
    This is the number of edges in the complete graph :math:`K_n`. Moreover, the
    vertex establishes :math:`m_1 \\cdot m_2` connections between blue and orange
    motifs. This is the number of edges in the complete bipartite graph :math:`K_{m_1,m_2}`
    and the vertex' contribution to the blue-orange off-diagonal entry.
    
    :param G: the SEN
    :param iterator: a :py:class:`sma.MotifIterator` as a source of motifs
    :param classificiator: a :py:class:`sma.MotifClassificator` for classifying 
        the motifs. Note that it must match with the given iterator.
    :param as_symmetric: per default the returned matrix is upper triangular. If
        this switch is set to ``True`` the returned matrix will be symmetrical, with
        the upper entries copied to the matrix' lower half.
    """
    ctable = cooccurrenceTableFull(G, iterator, classificator, to_array = True)
    choose2 = lambda n : n*(n-1)//2
    diag = numpy.diag(sum(choose2(ctable)))
    offdiag = numpy.array([[numpy.dot(ctable[:,i],ctable[:,j]) if i < j else 0 
                            for j in range(len(classificator.info().classes))] 
                            for i in range(len(classificator.info().classes))])
    if as_symmetric:
        return offdiag + diag + numpy.transpose(offdiag)
    else:
        return offdiag + diag
 
def motifClassGraph(G : nx.Graph, 
                    iterator : sma.MotifIterator, 
                    classificator : sma.MotifClassificator) -> nx.Graph:
    """
    Returns an :py:class:`networkx.Graph` with one node for every motif class as 
    described by the given :py:class:`sma.MotifClassificator`. The edges are weighted
    by the entries of :py:meth:`sma.motifClassMatrix`. The graph contains loops.
    
    :param G: the SEN
    :param iterator: a :py:class:`sma.MotifIterator` as a source of motifs
    :param classificiator: a :py:class:`sma.MotifClassificator` for classifying 
        the motifs. Note that it must match with the given iterator.
    """
    graph = nx.from_numpy_array(motifClassMatrix(G, iterator, classificator, as_symmetric=True))
    return nx.relabel_nodes(graph, dict(zip(itertools.count(), classificator.info().classes)), copy=True)

class _cooccurrenceEdgeTableFullMapper:
    def __init__(self, classificator, nodes_rows, nodes_columns, dyad):
        self.classificator = classificator
        self.indexer_rows    = {n : i for n, i in zip(nodes_rows, itertools.count())}
        self.indexer_columns = {n : i for n, i in zip(nodes_columns, itertools.count())}
        self.indexer_motifs  = {n : i for n, i in zip(classificator.info().classes, itertools.count())}
        self.dyad = dyad
    def __call__(self, motif):
        cl = self.classificator(motif)
        if type(self.dyad) is int:
            return (self.indexer_rows[motif[self.dyad][0]], 
                    self.indexer_columns[motif[self.dyad][1]], 
                    self.indexer_motifs[cl]) 
        else:
            return (self.indexer_rows[motif[self.dyad[0]]], 
                    self.indexer_columns[motif[self.dyad[1]]], 
                    self.indexer_motifs[cl])


def cooccurrenceEdgeTableFull(G : nx.Graph,
                              iterator : sma.MotifIterator,
                              classificator : sma.MotifClassificator,
                              dyad,
                              levels : tuple,
                              processes : int = 0,
                              chunksize : int = 10000):
    """
    Computes a co-occurrence table on edge level. Given an edge :math:`(v_1, v_2)`
    of a motif, :math:`v_1` in level :math:`i`, :math:`v_2` in level :math:`j`, this
    table consists of :math:`|V_i| \\times |V_j| \\times M` entries where :math:`V_i`,
    :math:`V_j` denotes the set of notes from level :math:`i`, resp. :math:`j` in
    the SEN and :math:`M` denotes the number of motif classes as classified by the
    given classificator. The :math:`(a,b,c)`th entry contains the number of times
    the edge :math:`(a,b)` occurs in a motif of class :math:`c`.
    
    The edge is specified using the ``dyad`` parameter. This parameter must contain
    a tuple of two integers specifying the index of the nodes spanning the edge in 
    the motifs provided by the iterator. For example, a typical 3E-motif looks like
    :math:`(e, s_1, s_2)` where :math:`s_1` and :math:`s_2` are social and :math:`e`
    is ecological. In this case, ``dyad = (1,2)`` would imply that the co-occurrence
    matrix for the edge :math:`(s_1, s_2)` would be computed. For technical reasons,
    a parameter ``levels`` must be provided. ``levels`` must be a tuple of length two
    specifying the ``sesType`` of the nodes in edge specified by ``dyad``. In the
    example, ``levels`` would be (:py:const:`sma.NODE_TYPE_SOC`,:py:const:`sma.NODE_TYPE_SOC`).
    
    Multiprocessing is supported. Use parameters ``processes`` and ``types``.
    
    **Example** Compute the co-occurrence table for 3S-motifs
    
    .. code :: Python 
    
        sma.cooccurrenceEdgeTableFull(G, 
                                      sma.ThreeSMotifs(G), 
                                      sma.ThreeMotifClassificator(G), 
                                      (1,2), # dyad, social nodes
                                      (0,0)) # levels, both social
    
    :param G: the SEN
    :param iterator: source of motifs
    :param classificator: classificator for the motifs
    :param dyad: specification of the esge for which the co-occurrence table is 
        computed (tuple of length 2)
    :param levels: ``sesTypes`` of the nodes in ``dyad`` (tuple of length 2)
    :param processes: number of processes for multiprocessing
    :param chunksize: chunksize for multiprocessing
    :returns: three values: the co-occurrence table, list of nodes as index for the rows,
        list of nodes as index for the columns
    """
    nodes_rows = list(sma.sesSubgraph(G, levels[0]))
    if levels[0] == levels[1]:
        nodes_columns = nodes_rows
    else:
        nodes_columns = list(sma.sesSubgraph(G, levels[0]))
    
    matrix = numpy.zeros((len(nodes_rows), len(nodes_columns), len(classificator.info().classes)), dtype=int)
    mapper = _cooccurrenceEdgeTableFullMapper(classificator, 
                                              nodes_rows, 
                                              nodes_columns, 
                                              dyad)
    
    if processes <= 0:
        for index in map(mapper, iterator):
            matrix[index] +=1
            del index
    else:
        with multiprocessing.Pool(processes) as p:
            classified = p.imap_unordered(mapper, iterator, chunksize = chunksize)
            for index in classified:
                matrix[index] +=1
                del index
            p.close()
            p.join()
    
    if levels[0] == levels[1]:
        for i in range(len(classificator.info().classes)):
            matrix[:,:,i] = numpy.triu(matrix[:,:,i] + matrix[:,:,i].T) - numpy.diag(numpy.diag(matrix[:,:,i]))
    
    return matrix, nodes_rows, nodes_columns

def edgeContributionList(G : nx.Graph, *arities, roles = [], level : int) -> numpy.ndarray:
    """
    Computes edge contribution lists for a certain family of motifs. This list
    contains one entry for every possible edge in the level of the network specified
    by ``level``. The entry associated with a dyad is number of times this dyad
    occurs in a certain family of motifs. The dyad itself is not taken into account
    here. In this way, open and closed motifs (i.e. motifs with a dyad in level
    ``level`` and otherwise equivalent motifs without this dyad) are grouped together.
    The value measures the contribution of a dyad in level ``level`` to open/closed
    motifs of similar class.
    
    This only makes sense if the motif specified by ``arities`` (and ``roles``)
    contains two nodes in level ``level``.
    
    For example, when working with 3-motifs (and ``level`` equalling the ``sesType``
    of the non-distinct nodes), motifs I.A and II.A, I.B and II.B and I.C and II.C
    are grouped together.
    
    This function does not work for directed graphs.
    
    :param G: the SEN
    :param arities: arities of the (multi-level) motif
    :param roles: optional roles for position matching, cf. :py:meth:`sma.matchPositions`
    :param level: level as described above
    :returns: tuple of:
        
        - two-dimensional array with one row for every group of motif (grouped
          by open/closed) and one column for every dyad on level ``level``
        - iterator giving the edges which index the columns of the array, call 
          ``list()`` on it to obtain a list of indices
    
    :raises NotImplementedError: if the motif signature is not supported
    """
    assert not G.is_directed(), 'edge contribution list is only supported for undirected graphs'
    
    signature  = sma.multiSignature(arities)
    motif_info = sma.motifInfo(signature, G.is_directed())
    positions  = sma.matchPositions(motif_info.signature, arities, roles)
    assert level in positions, 'selected motif does not reach selected level'
    index = positions.index(level)
    assert motif_info.signature[index] == 2, 'motif does not contain 2 vertices on the requested level'
    offset = sum(motif_info.signature[:index])

    iterator   = sma.MultiMotifsNormalized(G, *arities, roles = roles, motif_info = motif_info)
    classificator = motif_info.classificator(G)
    
    table, nodes, _ = sma.cooccurrenceEdgeTableFull(G,
                                                    iterator,
                                                    classificator,
                                                    (offset, offset+1),
                                                    (level, level))

    per_motif = numpy.array([table[:,:,i][numpy.triu_indices(table.shape[0],1)] for i in range(table.shape[2])])
    
    # group together
    indexer = {motif : i for i, motif in enumerate(motif_info.classes)}
    abstract_level = positions.index(level)
    if abstract_level not in motif_info.projections:
        message = motif_info.signature.copy()
        message[abstract_level] = '->%d' % message[abstract_level]
        raise NotImplementedError('ActorsChoice not implemented for signature [%s] (variable level highlighted)' \
                                  % (', '.join(map(str, message))))
    grouper = motif_info.projections[abstract_level]
    result  = numpy.array([sum(per_motif[indexer[gr]] for gr in group) for group in grouper])
    
    edges = itertools.combinations(nodes, 2)
    return result, edges

def identifyGaps(G : nx.Graph, 
                 motif_identifier : str, 
                 level : int = -1) -> list:
    """
    Computes a list of gaps (specific dyads) together with their contribution to 
    the number of motifs of a specific class.
    
    The contribution of a gap is the number of motifs of a fixed class which would
    be created by replacing the gap with an edge. This function computes this contribution
    for every gap on the specified level.
    
    The behaviour above applies when the specified motif contains the edge on the
    given level (i.e. the motif is a *closed motif*). If the edge is not present
    in the specified motif (the motif is *open*), the contribution is defined the
    number of motifs of the specified class are created by removing an edge from the
    network.
    
    This function does not work for directed graphs.
    
    :param G: the SEN
    :param motif_identifier: motif identifier string of the motif
    :param level: dyads of which level (``sesType``) are to be considered
    :returns: list of tuples ordered by the second entry in descending order
        consisting of
    
        - a tuple specifying an edge
        - the contribution of this edge to the number of motifs of the given type
          when being flipped
    
    """
    assert not G.is_directed(), 'identify gaps is only supported for undirected graphs'
    
    arities, roles, motif = sma.parseMotifIdentifier(motif_identifier)
    signature  = sma.multiSignature(arities)
    motif_info = sma.motifInfo(signature, G.is_directed())
    if level < 0:
        assert 2 in motif_info.signature, 'signature does not contain two'
        positions  = sma.matchPositions(motif_info.signature, arities, roles)
        level = positions[motif_info.signature.index(2)]
    contributions, edges = sma.edgeContributionList(G, 
                                                    *motif_info.signature, 
                                                    roles = positions, 
                                                    level = level)
    abstract_level = positions.index(level)
    grouper = motif_info.projections[abstract_level]
    index, group = next(filter(lambda x: motif in x[1], enumerate(grouper)))
    # we want to identify gaps, so ties which would close the largest number of gaps,
    # i.e. whose presence would increase the number of motifs specified by motif_idenitifer
    row = contributions[index]
    values = zip(edges, row)
    if group[0] == motif:
        # motif is an open motif
        values_filtered = filter(lambda x : G.has_edge(*x[0]), values)
    else:
        # motif is a closed motif
        values_filtered = filter(lambda x : not(G.has_edge(*x[0])), values)
    return sorted(values_filtered, key=operator.itemgetter(1), reverse=True)

def isClosedMotif(motif_identifier : str, level : int = -1) -> bool:
    """
    Queries the motif database and determines whether a motif is closed or open
    with respect to a given level.
    
    See :py:meth:`sma.identifyGaps`.
    
    This function does not work for directed graphs.
    
    :param motif_identifier: motif identifier string
    :param level: level (``sesType``) for the gap
    :returns: true/false whether the motif is closed.
    :raises NotImplementedError: if the motif database does not know..
    """
    arities, roles, motif = sma.parseMotifIdentifier(motif_identifier)
    signature             = sma.multiSignature(arities)
    motif_info            = sma.motifInfo(signature, False)
    if level >= 0:
        positions         = sma.matchPositions(motif_info.signature, arities, roles)
        abstract_level    = positions.index(level)
    else:
        abstract_level    = motif_info.signature.index(2)
    if abstract_level not in motif_info.projections:
        message = motif_info.signature.copy()
        message[abstract_level] = '->%d' % message[abstract_level]
        raise NotImplementedError('Closed/open relations not implemented for signature [%s] (variable level highlighted)' \
                                  % (', '.join(map(str, message))))
    for o, c in motif_info.projections[abstract_level]:
        if c == motif:
            return True
        if o == motif:
            return False
    raise TypeError('unknown motif %s' % motif)
    