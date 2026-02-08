#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import networkx as nx
import sma
import pandas
import warnings

def translateGraph(adjacency, 
                   attributeNames, 
                   attributeValues, 
                   typeAttr : str = None,
                   directed : bool = False) -> nx.Graph:
    """
    Returns a :py:class:`networkx.Graph` from a adjacency matrix, a list of nodal attribute names
    and a matrix of nodal attribute values. This function is designed to make networkx objects
    compatible with R's statnet network objects.
    
    :param adjacency: adjacency matrix provided as a numerical matrix
    :param attributeNames: list of attribute names
    :param attributeValues: matrix of attribute values in accordance to `attributeNames`.
    :param typeAttr: name of an attribute with specifies whether a node is social or ecological.
        The values must be integers, matching :py:const:`sma.NODE_TYPE_SOC` and :py:const:`sma.NODE_TYPE_ECO` in
        two-level networks. If None, attributeNames must contain 'sesType'.
    :param directed: whether the graph is directed
    :returns: networkx graph with the given properties
    :raises ValueError: in case of invalid parameters
    """
    create_using = nx.DiGraph() if directed else nx.Graph()
    
    G = nx.from_numpy_array(adjacency, 
                            create_using = create_using)
    if typeAttr is None:
        typeAttr = 'sesType'
    
    if typeAttr not in attributeNames:
        raise ValueError("level attribute '%s' is not in list of attribute names %s"\
                         % (typeAttr, str(attributeNames)))
    
    for attr, values in zip(attributeNames,attributeValues):
        if typeAttr == attr:
            # guarantee integer values
            nx.set_node_attributes(G, 
                                   name='sesType', 
                                   values={i : int(v) for (i,v) in enumerate(values)})
        elif attr == 'sesType':
            warnings.warn("Skipping nodal attribute called 'sesType' given in "+\
                          "attribute list since this name is reserved.")
        else:
            nx.set_node_attributes(G, name=attr, values=dict(enumerate(values)))    
    
    return G

def countAnyMotifs(it : sma.ComplexMotifIterator) -> int:
    """
    Counts the number of elements in the given iterator.
    
    Function for compatability with R.
    """
    try:
        return len(it)
    except TypeError:
        return sum(1 for _ in it)

def motifSet(source : sma.SourceMotifIterator, 
             *conditions : sma.ConditionMotifIterator) -> sma.ComplexMotifIterator:
    """
    Returns an motif interator representing a set of motifs with 
    certain properties.
    
    Function for compatability with R.
    
    :param source: :py:class:`sma.SourceMotifIterator`, the basal set to take the
        motifs from
    :param conditions: one or several :py:class:`sma.ConditionMotifIterator` 
        representing conditions which the motifs must fulfill to be part of the set
    """
    it = source
    for cond in conditions:
        it = it & cond
    return it

def listMotifs(iterator : sma.ComplexMotifIterator) -> list:
    """
    Returns a list of all motifs in a motif iterator.
    
    Function for compatability with R.
    
    :param iterator: motif iterator
    """
    return list(iterator)

def _gatherMotifDict(d : dict) -> dict:
    result = {}
    for head, d2 in d.items():
        for motif, value in d2.items():
            result['%s[%s]' % (head, str(motif))] = value
    return result

def _ensureInt(args : dict, keys : list) -> dict:
    for key in keys:
        if key in args:
            args[key] = int(args[key])
    return args

def countMotifsAutoR(G : nx.Graph, 
                     motifs : list, 
                     omit_total_result : bool = False,
                     **kwargs) -> pandas.DataFrame:
    """
    Wrapper function for :py:meth:`sma.countMotifsAuto`. Optimized for the reticulate
    R interface.
    
    :param G: the SEN
    :param motifs: the list of motifs to be counted
    :param omit_total_result: whether only the partial result shall be returned
    :param kwargs: further parameters for :py:meth:`sma.countMotifsAuto`
    :returns: pandas dataframe with either partial or total counts
    """
    if 'progress_report' not in kwargs:
        kwargs['progress_report'] = True
    
    partial, total = sma.countMotifsAuto(G, *motifs, **kwargs)
    if omit_total_result:
        df = pandas.DataFrame(data = partial, index = ['count'])
        return df
    else:
        gathered = _gatherMotifDict(total)
        df = pandas.DataFrame(data = gathered, index = ['count'])
        return df

def distributionMotifsAutoR(G : nx.Graph, 
                            motifs : list,
                            model : str = sma.MODEL_ERDOS_RENYI,
                            level : int = -1,
                            omit_total_result : bool = False) -> pandas.DataFrame:
    """
    Wrapper function for :py:meth:`sma.distributionMotifsAuto`. Optimized for the reticulate
    R interface.
    
    :param G: the SEN
    :param motifs: the list of motifs whose distributions are to be described
    :param omit_total_result: whether only the partial result shall be returned
    :returns: pandas dataframe with either partial or total distribution
        information
    """
    level = int(level)
    partial, total = sma.distributionMotifsAuto(G, *motifs, model = model, level = level)
    if omit_total_result:
        df = pandas.DataFrame(data = partial, index = ['expectation', 'variance'])
        return df
    else:
        gathered = _gatherMotifDict(total)
        df = pandas.DataFrame(data = gathered, index = ['expectation', 'variance'])
        return df

def simulateBaselineAutoR(G : nx.Graph,
                          motifs : list,
                          **kwargs) -> pandas.DataFrame:
    """
    Wrapper function for :py:meth:`sma.simulateBaselineAuto`.
    Optimized for the reticulate R interface.
    
    :param G: the SEN
    :param motifs: the list of motifs whose distributions are to be described
    :param kwargs: further parameters for :py:meth:`sma.simulateBaselineAutoR`.
    :returns: pandas dataframe with one column for every motif and one row for 
        every random SEN
    """
    kwargs = _ensureInt(kwargs, ['n', 'level', 'processes', 'chunksize'])
    simulation = sma.simulateBaselineAuto(G,
                                          *motifs,
                                          **kwargs)
    df = pandas.DataFrame(data = simulation)
    return df

def identifyGapsR(G : nx.Graph, 
                  motif_identifier : str, 
                  level : int = -1) -> pandas.DataFrame:
    """
    Wrapper function for :py:meth:`sma.identifyGaps`. Optimized for the reticulate
    R interface.
    
    :param G: the SEN
    :param motif_identifier: a motif identifier
    :param level: level
    :returns: pandas dataframe with three columns: two for the edges, one for their
        contribution
    """
    level = int(level)
    result = sma.identifyGaps(G, motif_identifier, level = level)
    df = pandas.DataFrame(map(lambda x: (*x[0],x[1]), result), 
                          columns=['vertex0', 'vertex1', 'contribution'])
    return df

def isClosedMotifR(motif_identifier : str, level : int = -1) -> bool:
    """
    Wrapper function for :py:meth:`sma.isClosedMotif`. Optimized for the reticulate
    R interface.
    
    :param motif_identifier: motif identifier
    :param level: level
    :returns: whether the motif is closed with respect to the specified level
    :raises NotImplementedError: if open/closed relations are not implemented for
        this motif and level
    """
    return sma.isClosedMotif(motif_identifier, int(level))
