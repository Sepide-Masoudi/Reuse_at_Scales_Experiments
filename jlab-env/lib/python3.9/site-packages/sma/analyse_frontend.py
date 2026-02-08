#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import networkx as nx
import sma
import pandas

def countMultiMotifs(G : nx.Graph, 
                     *arities, 
                     roles = [], 
                     iterator = None, 
                     **kwargs):
    """
    Front-end function for counting multi-motifs. The default iterator is
    :py:class:`sma.MultiMotifs`. As classificator serves :py:class:`sma.MultiMotifClassificator`.
    All options of :py:meth:`sma.countMotifs` are available.
    
    Call :py:meth:`sma.supportedSignatures` for an overview of all supported 
    signatures.
    
    This function works for directed and undirected graphs. The directed case is
    distinguished by calling :py:meth:`networkx.is_directed` on the given graph.
    
    See also :py:meth:`sma.countMultiMotifsSparse`.
    
    :param G: the graph
    :param arities: arities for the motif source and the classificator
    :param roles: roles of the level, cf. :py:class:`sma.MultiMotifClassificator`.
    :param iterator: a custom iterator, default is :py:class:`sma.MultiMotifs`.
    :param kwargs: additional parameters for :py:meth:`sma.countMotifs`
    """
    signature = sma.multiSignature(arities)
    
    # now handle all other motifs
    motif_info = sma.motifInfo(signature, G.is_directed())
    
    # check if motif info provides direct coutning method
    if motif_info.counter is not None:
        positions = sma.matchPositions(motif_info.signature, arities, roles)
        return motif_info.counter(G, *positions, **kwargs)
    
    if iterator is None:
        iterator = sma.MultiMotifsNormalized(G, *arities, roles = roles, motif_info = motif_info)
    return sma.countMotifs(G, 
                           motif_info.classificator(G), 
                           iterator, 
                           progress_total = sma.totalMultiMotifs(G, *arities),
                           **kwargs)
        

def countMultiMotifsSparse(G : nx.Graph,
                           *arities, 
                           roles = [],
                           **kwargs):
    """
    Front-end function for several counting functions for sparse networks. It supports
    the same parameters for defining the motifs (arities, roles) as other multi-level
    counting functions. Please check the documentations of the respective functions
    as some of them might return partial counts only. A full list of supported
    motif signatures can be accessed via :py:meth:`sma.supportedSignatures`.
    
    This function works for directed and undirected graphs. The directed case is
    distinguished by calling :py:meth:`networkx.is_directed` on the given graph.
    
    See also :py:meth:`sma.countMultiMotifs`.
    
    :param G: the SEN
    :param arities: arities of the motifs, cf. :py:class:`sma.MultiMotifClassificator`.
    :param roles: roles of the levels, cf. :py:class:`sma.MultiMotifClassificator`.
    :param kwargs: additional parameters for the counter functions, see above.
    """
    signature  = sma.multiSignature(arities)
    motif_info = sma.motifInfo(signature, G.is_directed())
    positions  = sma.matchPositions(motif_info.signature, arities, roles)
    if motif_info.sparse_counter is None:
        raise NotImplementedError('sparse counting for signature %s is not implemented'\
                                  % str(motif_info.signature))
    return motif_info.sparse_counter(G, *positions, **kwargs)

def findIdealCounter(signature : list, 
                     motifs : list, 
                     directed : bool,
                     assume_sparse : bool = True):
    """
    Determines an ideal counter for a family of motifs. This function checks whether
    the given motifs can be counted with counters for sparse networks 
    (if ``assume_sparse = True``) and returns in this case the counter supplemented
    with additional parameters for the counter.
    
    This function is a called by :py:meth:`sma.countMotifsAuto`.
    
    :param signature: (ordered) signature
    :param motifs: list of motif classes
    :param directed: whether the considered network is directed
    :param assume_sparse: whether the network is assumed to be sparse
    :returns: tuple consisting of
    
        - a counting function, e.g. :py:meth:`sma.countMultiMotifs` or 
          :py:meth:`sma.countMultiMotifsSparse`,
        - a dict with additional parameters for this counting function
    """
    if directed:
        return sma.countMultiMotifs, {}
    
    # optimisation only in undirected case
    if signature == [1,2] and assume_sparse:
        return sma.countMultiMotifsSparse, {}
    elif signature == [2,2]:
        if assume_sparse and (not('IV.A' in motifs) and 
                              not('IV.B' in motifs) and 
                              not('IV.C' in motifs) and 
                              not('IV.D' in motifs)):
            return sma.countMultiMotifsSparse, {}
    elif signature == [1,1,2]:
        if assume_sparse:
            for motif in motifs:
                if int(motif) != 3 and int(motif) != 4:
                    return sma.countMultiMotifsSparse, {}
            return sma.countMultiMotifsSparse, {'optimize_top_adjacent' : True}
    elif signature == [1,2,2]:
        if assume_sparse:
            if all(map(lambda m : m.endswith('.3'), motifs)):
                return sma.countMultiMotifsSparse, {'optimize_top_adjacent' : True}
            if all(map(lambda m : m.endswith('.2') or m.endswith('.3'), motifs)):
                return sma.countMultiMotifsSparse, {'optimize_top_adjacent' : False}
    elif signature == [2,2,2]:
        if assume_sparse:
            for motif in motifs:
                if int(motif) != 3 and int(motif) != 4:
                    return sma.countMultiMotifs, {}
            return sma.countMultiMotifsSparse, {}
    elif signature == [1,3]:
        if assume_sparse:
            return sma.countMultiMotifsSparse, {}
    return sma.countMultiMotifs, {}

def countMotifsAuto(G : nx.Graph, 
                    *motifs, 
                    assume_sparse : bool = True,
                    **kwargs):
    """
    Front-end function for all counting functions in sma. This function determines
    automatically an ideal counter (sparse or dense) for a set of motifs. This 
    reduces overhead and leads to an optimisation.
    
    .. code :: Python
        
        # let G by a SEN
        # count open and closed social and ecological triangles
        partial, total = sma.countMotifsAuto(G, "1,2[I.C]", "1,2[II.C]", "2,1[I.C]", "2,1[II.C]")
        print(partial)
        print(total)
 
    This function works for directed and undirected graphs. The directed case is
    distinguished by calling :py:meth:`networkx.is_directed` on the given graph.
    
    :param G: the SEN
    :param motifs: list of motif identifier, see documentation
    :param assume_sparse: whether the network shall be assumed to be sparse
    :param kwargs: more arguments for the counter
    :returns: tuple consisting of:
        
        - a dict with the motif identifiers as keys and the corresponding counts
          as values
        - a dict with all counts collected
    
    :raises ValueError: in case of unrecognisable motif identifiers
    """
    grouped_request = sma.groupMotifIdentifiers(*motifs)
    partial_results = {}
    total_results = {}
    
    # overwrite inadmissible parameters
    kwargs['array'] = False
    progress_report = 'progress_report' in kwargs and kwargs['progress_report']
    
    for cl in grouped_request.keys():
        if progress_report:
            print("Processing %s motifs" % cl)
        arities, roles, _ = sma.parseMotifIdentifier(cl)
        signature = sma.multiSignature(arities)
        motif_info = sma.motifInfo(signature, G.is_directed())
        
        keys = []
        for motif in grouped_request[cl]:
            try:
                casted = motif_info.classes_type(motif)
            except ValueError:
                raise ValueError("There is no motif with identifier %s[%s]."\
                                 % (cl, motif))
            if casted not in motif_info.classes:
                raise ValueError("There is no motif with identifier %s[%s]."\
                                 % (cl, motif))
            keys.append(casted)
                
        counter, kw = sma.findIdealCounter(signature, 
                                           grouped_request[cl], 
                                           G.is_directed(),
                                           assume_sparse)
        counted = counter(G, *arities, roles = roles, **{**kwargs, **kw})
        total_results[cl] = counted
        # put partial result together
        for motif, key in zip(grouped_request[cl], keys):
            partial_results["%s[%s]" % (cl, motif)] = counted[key]
    
    return partial_results, total_results

def exemplifyMotif(G : nx.Graph, identifier : str) -> tuple:
    """
    Returns an example for a motif with given identifier in a SEN.
    
    This function works for directed and undirected graphs. The directed case is
    distinguished by calling :py:meth:`networkx.is_directed` on the given graph.
    
    :param G: the SEN
    :param identifier: motif identifier string
    :returns: motif tuple in normalised form (ordered as in signature) or None
        if there is no such motif in the network
    :raises ValueError: if the given motif identifier string does not specify a 
        motif class, i.e. if only ``1,2`` is given and not ``1,2[I.A]``.
    """
    arities, roles, motif = sma.parseMotifIdentifier(identifier)
    if motif is None:
        raise ValueError('the motif identifier string %s does not specify a motif class.'\
                         % identifier)
    signature = sma.multiSignature(arities)
    motif_info = sma.motifInfo(signature, G.is_directed())
    source = sma.MultiMotifsNormalized(G, *arities, roles = roles, motif_info = motif_info)
    motif = motif_info.classes_type(motif)
    selector = sma.isClass(motif_info.classificator(G), motif)
    try:
        return next(source & selector)
    except StopIteration:
        return None

def motifTable(G : nx.Graph, identifier : str) -> pandas.DataFrame:
    """
    Returns a :py:class:`pandas.DataFrame` with one row for each instance of the
    motif specified by the given motif identifier string. If the identifier string
    specifies a motif class, e.g. ``1,2[I.A]`` , then only motifs of the given
    class are returned. If the identifier string specifies a signature, e.g.
    ``1,2``, then a full list of all motifs of this signature is returned. In the
    latter case, the dataframe contains an additional column contain the motif
    classes.
    
    The naming scheme of the columns is as follows: Each column is called
    ``levelA_nodeB`` where ``A`` is the ``sesType`` of the nodes in the column
    and ``B`` the index of the nodes amoung the nodes on the same level. This index
    stems from the internal order of the nodes and does not carry any specific meaning.
    
    .. code :: Python
    
           sma.motifTable(G, '1,2')
           
           # level0_node0 level1_node0 level1_node1 class
           # 0        Lake 0       Town 0       Town 1   I.B
           # 1        Lake 0       Town 0       Town 2   I.B
           # 2        Lake 0       Town 0       Town 3  II.A
           # 3        Lake 0       Town 0       Town 4   I.B
           # 4        Lake 0       Town 1       Town 2   I.C
           # ..          ...          ...          ...   ...
           # 95       Lake 9       Town 1       Town 3  II.B
           # 96       Lake 9       Town 1       Town 4  II.C
           # 97       Lake 9       Town 2       Town 3  II.B
           # 98       Lake 9       Town 2       Town 4  II.C
           # 99       Lake 9       Town 3       Town 4   I.B
           #  
           # [100 rows x 4 columns]
    
    This function works for directed and undirected graphs. The directed case is
    distinguished by calling :py:meth:`networkx.is_directed` on the given graph.
    
    :param G: the SEN
    :param identifier: a motif identifier string
    :returns: DataFrame as described above.
    """
    arities, roles, motif = sma.parseMotifIdentifier(identifier)
    signature = sma.multiSignature(arities)
    positions = sma.matchPositions(signature, arities, roles)
    motif_info = sma.motifInfo(signature, G.is_directed())
    source = sma.MultiMotifsNormalized(G, *arities, roles = roles, motif_info = motif_info)
    classificator = motif_info.classificator(G)
    
    column_names = []
    for p, s in zip(positions, signature):
        for i in range(s):
            column_names.append('level%d_node%d' % (p, i))
    
    if motif is None:
        column_names.append('class')
        data = map(lambda m : [*m, classificator(m)], source)
        return pandas.DataFrame(data, columns = column_names)
    else:
        motif_casted = motif_info.classes_type(motif)
        selector = sma.isClass(classificator, motif_casted)
        data = source & selector
        return pandas.DataFrame(data, columns = column_names)