#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import networkx as nx
import itertools, numpy
import sma.properties, sma.analyse

def _plainSEN(ecoNodes : int,
              socNodes : int,
              ecoName : str,
              socName : str,
              from_graph : nx.Graph = None) :
    """
    Auxilliary function for returning a graph with a certain amount of social 
    and ecological nodes. Besides the graph lists of the respective nodes are returned.
    
    :param ecoNodes: number of ecological nodes
    :param socNodes: number of social nodes
    :param ecoName: name for the ecological nodes, i.e. 'Lake' for getting names
        like 'Lake 0', 'Lake 1' etc.
    :param socName: name for the social nodes, i.e. 'Town' for getting names
        like 'Town 0', 'Town 1' etc.
    :param from_graph: graph object to add the vertices to or ``None`` to use a
        blank instance of :py:class:`networkx.Graph`.
    :returns: triple consisting of the graph, a list of the names of ecological nodes
        and a list of the names of the social nodes
    """
    G = nx.Graph() if from_graph is None else from_graph
    ecos = ['%s %d' % (ecoName, i) for i in range(ecoNodes)]
    socs = ['%s %d' % (socName, i) for i in range(socNodes)]
    for eco in ecos:
        G.add_node(eco, sesType=sma.properties.NODE_TYPE_ECO)
    for soc in socs:
        G.add_node(soc, sesType=sma.properties.NODE_TYPE_SOC)
    return G, ecos, socs

def addRandomEdges(G : nx.Graph, 
                  ecoNodes : list, 
                  socNodes : list, 
                  edgesCounts : dict) -> nx.Graph:
    """
    Add a specified number of random edges to a given SEN. 
    
    :param G: the graph
    :param ecoNodes: a list of the ecological nodes in the SEN
    :param socNodes: a list of social nodes in the SEN
    :param edgesCounts: dict containing the amounts of social-social, ecological-ecological 
        and social-ecological edges, labelled in accordance with :py:meth:`sma.edgesCount`.
    """
    # add soc-soc edges
    possibleSocSocEdges = list(itertools.combinations(socNodes, 2))
    numpy.random.shuffle(possibleSocSocEdges)
    G.add_edges_from(itertools.islice(possibleSocSocEdges, edgesCounts[sma.properties.EDGE_TYPE_SOC_SOC]))
    
    # add eco-soc edges
    possibleEcoSocEdges = list(itertools.product(socNodes, ecoNodes))
    numpy.random.shuffle(possibleEcoSocEdges)
    G.add_edges_from(itertools.islice(possibleEcoSocEdges, edgesCounts[sma.properties.EDGE_TYPE_ECO_SOC]))
    
    # add eco-eco edges
    possibleEcoEcoEdges = list(itertools.combinations(ecoNodes, 2))
    numpy.random.shuffle(possibleEcoEcoEdges)
    G.add_edges_from(itertools.islice(possibleEcoEcoEdges, edgesCounts[sma.properties.EDGE_TYPE_ECO_ECO]))
    
    return G

def randomSENs(ecoNodes : int, 
               socNodes : int, 
               density : float = None, 
               ecoName : str = 'Lake', 
               socName : str = 'Town') :
    """
    Generator which yields random graphs with a certain amount of ecological and
    social nodes. Optionally, a densitiy can be specified.

    See also :py:meth:`sma.randomDiSENs`.

    :param ecoNodes: number of ecological nodes
    :param socNodes: number of social nodes
    :param density: densitiy, i.e. number of edges / number of possible edges,
        cf. :py:meth:`sma.density`. Set to None if the density does not matter
    :param ecoName: name for the ecological nodes, i.e. 'Lake' for getting names
        like 'Lake 0', 'Lake 1' etc.
    :param socName: name for the social nodes, i.e. 'Town' for getting names
        like 'Town 0', 'Town 1' etc.
    """
    nodesCount = ecoNodes + socNodes
    edgesCount = nodesCount * (nodesCount - 1) // 2
    while True:
        G, ecos, socs = _plainSEN(ecoNodes, socNodes, ecoName, socName)
        
        possibleEdges = list(itertools.combinations(itertools.chain(ecos, socs), 2))
        numpy.random.shuffle(possibleEdges)
        
        thisEdgesCount = edgesCount
        if density is None:
            thisEdgesCount = numpy.random.randint(0, edgesCount)
        else:
            thisEdgesCount = int(edgesCount * density)
        
        G.add_edges_from(itertools.islice(possibleEdges, thisEdgesCount))
        yield G
        
def randomSpecialSENs(ecoNodes : int,
                      socNodes : int,
                      edgesCounts : dict,
                      ecoName : str = 'Lake',
                      socName : str = 'Town') :
    """
    Generator which yields random graphs with a certain amount of ecological and 
    social nodes and with certain amounts of social-social, ecological-ecological 
    and social-ecological edges. See :py:meth:`sma.edgesCount`.
    
    This function implemented :py:const:`sma.MODEL_FIXED_DENSITIES`.
    
    :param ecoNodes: amount of ecological nodes
    :param socNodes: amount of social nodes
    :param edgesCounts: dict containing the amounts of social-social, ecological-ecological 
        and social-ecological edges, labelled in accordance with :py:meth:`sma.edgesCount`.
    :param ecoName: name for the ecological nodes, i.e. 'Lake' for getting names
        like 'Lake 0', 'Lake 1' etc.
    :param socName: name for the social nodes, i.e. 'Town' for getting names
        like 'Town 0', 'Town 1' etc.
    """
    assert edgesCounts[sma.properties.EDGE_TYPE_SOC_SOC] <= socNodes * (socNodes - 1),\
        'too many social-social edges requested, SEN size insufficient'
    assert edgesCounts[sma.properties.EDGE_TYPE_ECO_SOC] <= (socNodes + ecoNodes) * (socNodes + ecoNodes - 1),\
        'too many ecological-social edges requested, SEN size insufficient'
    assert edgesCounts[sma.properties.EDGE_TYPE_ECO_ECO] <= ecoNodes * (ecoNodes - 1),\
        'too many ecological-ecological edges requested, SEN size insufficient'
    while True:
        G, ecos, socs = _plainSEN(ecoNodes, socNodes, ecoName, socName)
        addRandomEdges(G, ecos, socs, edgesCounts)
        
        yield G
        
def randomSimilarSENs(G : nx.Graph,
                      ecoName : str = 'Lake',
                      socName : str = 'Town'):
    """
    Generator which yields random graphs similar to the given graph, w.r.t. the
    number of social and ecological nodes and the number of edges in the domains.
    
    This function implemented :py:const:`sma.MODEL_FIXED_DENSITIES`.
    
    See :py:meth:`sma.edgesCount` and :py:meth:`sma.randomSpecialSENs`.
    See :py:meth:`sma.randomSimilarAttributedSENs` for "more similar" random SENs.
    
    :param G: the graph the random graphs shall be similar to.
    :param ecoName: name for the ecological nodes, i.e. 'Lake' for getting names
        like 'Lake 0', 'Lake 1' etc.
    :param socName: name for the social nodes, i.e. 'Town' for getting names
        like 'Town 0', 'Town 1' etc.
    """
    nodesCounts = sma.nodesCount(G)
    edgesCounts = sma.analyse.edgesCount(G)
    return randomSpecialSENs(nodesCounts[0], nodesCounts[1], edgesCounts, ecoName, socName)

def randomSimilarAttributedSENs(G : nx.Graph):
    """
    Generator which yields random graphs similar to the given graph, w.r.t. all
    nodal attributes. The nodal data is extracted and a random SENs with equal 
    amount of edges in each domain is generated.
    
    This function implemented :py:const:`sma.MODEL_FIXED_DENSITIES`.
    
    :param G: the graph the random graphs shall be similiar to.
    """
    edgesCounts = sma.analyse.edgesCount(G)
    
    ecoNodes = list(sma.analyse.sesSubgraph(G, sma.properties.NODE_TYPE_ECO))
    socNodes = list(sma.analyse.sesSubgraph(G, sma.properties.NODE_TYPE_SOC))
    
    template = G.copy()
    template.remove_edges_from(G.edges)
    
    while True:
        rand = template.copy()
        addRandomEdges(rand, ecoNodes, socNodes, edgesCounts)
        yield rand

def randomMultiSENsFixedDensities(nVertices : list, 
                                  nEdges : numpy.ndarray, 
                                  names : list = sma.MULTI_DEFAULT_NAMES):
    """
    Generator for multi-level SENs.
    
    This function implemented :py:meth:`sma.MODEL_FIXED_DENSITIES`.
    
    **Example:** Generate a SEN with 3 ecological nodes, 4 social actors and 2
    issues. Then ``nVertices`` must be set to ``[3,4,2]``. The number of edges is 
    given by the matrix in ``nEdges``. For a given multi-level SEN such a matrix 
    can be computed using :py:meth:`sma.edgesCountMatrix`. Entry :math:`(i,j)`
    contains the number of edges connected vertices of types :math:`i` and :math:`j`.
    
    .. code :: Python
    
        import sma, numpy
        nEdges = numpy.array([[3,2,1],[0,4,2],[0,0,1]])
        # 3 edges from eco to eco, 2 edges from eco to soc, 1 edge from eco to issue
        # 4 edges from soc to soc, 2 edges from soc to issue, 1 edge from issue to issue
        
        G = next(sma.randomMultiSENs([3,4,2], nEdges))
    
    Given ``nVertices``, :py:meth:`sma.randomEdgeCountMatrix` can be used to compute
    a random admissible matrix for ``nEdges``:
        
    .. code :: Python
        
        nVertices = [3,4,2]
        G = next(sma.randomMultiSENs(nVertices, sma.randomEdgeCountMatrix(nVertices)))
    
    :param nVertices: a list of integers specifying how many nodes of each type
        should be generated
    :param nEdges: an upper-triangular matrix specifying how many random edges 
        connecting nodes of certain type should be generated
    :param names: names of the nodes of a certain type, cf. :py:const:`sma.MULTI_DEFAULT_NAMES`.
    
    """
    assert numpy.shape(nEdges) == (len(nVertices), len(nVertices)), 'dimensions of nVertices and nEdges must match'
    assert len(nVertices) <= len(names), 'please provide sufficently many names'
    maximal = sma.maxEdgeCountMatrix(nVertices)
    assert numpy.all(nEdges <= maximal), 'too many edges requested'
    
    template = nx.Graph()
    nodes = {}
    for n, name, typ in zip(nVertices, names, itertools.count()):
        nodes[typ] = ['%s %d' % (name, i) for i in range(n)]
        template.add_nodes_from(nodes[typ], sesType = typ)
    
    while True:
        rand = template.copy()
        for i in range(len(nVertices)):
            possibleEdges = list(itertools.combinations(nodes[i], 2))
            numpy.random.shuffle(possibleEdges)
            rand.add_edges_from(itertools.islice(possibleEdges, int(nEdges[i,i])))
            for j in range(i+1, len(nVertices)):
                possibleEdges = list(itertools.product(nodes[i], nodes[j]))
                numpy.random.shuffle(possibleEdges)
                rand.add_edges_from(itertools.islice(possibleEdges, int(nEdges[i,j])))
        yield rand

def _addRandomInterLevelEdges(G, nodesA, nodesB, density):
    if density == 0:
        return
    if density == 1:
        G.add_edges_from(itertools.product(nodesA, nodesB))
        return
    possibleEdges = itertools.product(nodesA, nodesB)
    selector = numpy.random.rand(len(nodesA) * len(nodesB)) <= density
    G.add_edges_from(itertools.compress(possibleEdges, selector))

def _addRandomIntraLevelEdges(G, nodes, density):
    if density == 0:
        return
    if density == 1:
        G.add_edges_from(itertools.combinations(nodes, 2))
        return
    possibleEdges = itertools.combinations(nodes, 2)
    n = len(nodes)
    selector = numpy.random.rand(n * (n - 1) // 2) <= density
    G.add_edges_from(itertools.compress(possibleEdges, selector))

def randomMultiSENsErdosRenyi(nVertices : list,
                              nEdges : numpy.ndarray,
                              names : list = sma.MULTI_DEFAULT_NAMES):
    """
    Generator for random graphs drawn from an Erdős-Rényi model. The probabilities
    for the edges linking the various levels are extracted from ``nEdges``.
    This function implements :py:const:`sma.MODEL_ERDOS_RENYI`.
    
    
    :param nVertices: vector indicating the numbers of vertices on the various levels
    :param nEdges: matrix indicating numbers of edges, see :py:meth:`sma.edgesCountMatrix`.
    :param names: names for the nodes on the various levels, default :py:const:`sma.MULTI_DEFAULT_NAMES`.
    """
    assert numpy.shape(nEdges) == (len(nVertices), len(nVertices)),\
        'dimensions of nVertices and nEdges must match'
    assert len(nVertices) <= len(names),\
        'please provide sufficently many names'
    maximal = sma.maxEdgeCountMatrix(nVertices)
    assert numpy.all(nEdges <= maximal), 'too many edges requested'
    
    template = nx.Graph()
    nodes = {}
    for n, name, typ in zip(nVertices, names, itertools.count()):
        nodes[typ] = ['%s %d' % (name, i) for i in range(n)]
        template.add_nodes_from(nodes[typ], sesType = typ)
    
    densities = numpy.divide(nEdges, maximal, where = (maximal != 0))

    while True:
        rand = template.copy()
        for i in range(len(nVertices)):
            _addRandomIntraLevelEdges(rand, nodes[i], densities[i, i])
            for j in range(i+1, len(nVertices)):
                _addRandomInterLevelEdges(rand, nodes[i], nodes[j], densities[i, j])
        yield rand

def randomMultiSENsActorsChoice(G : nx.Graph, level : int):
    """
    Generator for random graphs drawn from an Actor's Choice mode. The probability
    for the edges on the variable level is extracted from the given network.
    This function implements :py:const:`sma.MODEL_ACTORS_CHOICE`.
    
    :param G: the SEN
    :param level: ``sesType`` of the variable level
    """
    assert level >= 0, "invalid level %d for Actor's Choice model" % level
    template  = G.copy()
    densities = sma.densityMatrix(G)
    density   = densities[level, level]
    actors    = list(sma.sesSubgraph(G, level))
    template.remove_edges_from(itertools.combinations(actors, 2))
    
    while True:
        rand = template.copy()
        _addRandomIntraLevelEdges(rand, actors, density)
        yield rand
        

def randomSimilarMultiSENs(G : nx.Graph, 
                           names : list = sma.MULTI_DEFAULT_NAMES,
                           model : str = sma.MODEL_FIXED_DENSITIES,
                           level : int = -1):
    """
    Generates random multi-level SENs "similar" to the given SEN. This function
    is a front-end for several generator functions which are chosen based on the 
    given ``model`` parameter:
        
        - :py:const:`sma.MODEL_FIXED_DENSITIES`: 
          see :py:meth:`sma.randomMultiSENsFixedDensities`
        - :py:const:`sma.MODEL_ERDOS_RENYI`:
          see :py:meth:`sma.randomMultiSENsErdosRenyi`
        - :py:const:`sma.MODEL_ACTORS_CHOICE`:
          see :py:meth:`sma.randomMultiSENsActorsChoice`
    
    :param G: the SEN
    :param names: names for the classes of nodes, default :py:const:`sma.MULTI_DEFAULT_NAMES`
    :param model: baseline model, default :py:const:`sma.MODEL_FIXED_DENSITIES`.
    :param level: ``sesType`` of the variable level if model is set to 
        :py:const:`sma.MODEL_ACTORS_CHOICE`.
    :returns: generator yielding random SENs
    :raises NotImplementedError: if no generators for the given model are implemented
    """
    if model == sma.MODEL_ACTORS_CHOICE:
        return randomMultiSENsActorsChoice(G, level)
    else:
        nVertices = sma.nodesCount(G, array = True)
        nEdges = sma.edgesCountMatrix(G, len(nVertices))
        if model == sma.MODEL_FIXED_DENSITIES:
            return randomMultiSENsFixedDensities(nVertices, nEdges, names)
        if model == sma.MODEL_ERDOS_RENYI:
            return randomMultiSENsErdosRenyi(nVertices, nEdges, names)
    raise NotImplementedError('no random SENs generators for baseline model %s implemented'\
                              % model)

def randomDiSENs(ecoNodes : int, 
                 socNodes : int, 
                 density : float = None, 
                 ecoName : str = 'Lake', 
                 socName : str = 'Town') :
    """
    Generator which yields random directed graphs with a certain amount of ecological and
    social nodes. Optionally, a densitiy can be specified.

    See also :py:meth:`sma.randomSENs`.

    :param ecoNodes: number of ecological nodes
    :param socNodes: number of social nodes
    :param density: densitiy, i.e. number of edges / number of possible edges,
        cf. :py:meth:`sma.density`. Set to None if the density does not matter
    :param ecoName: name for the ecological nodes, i.e. 'Lake' for getting names
        like 'Lake 0', 'Lake 1' etc.
    :param socName: name for the social nodes, i.e. 'Town' for getting names
        like 'Town 0', 'Town 1' etc.
    """
    nodesCount = ecoNodes + socNodes
    edgesCount = nodesCount * (nodesCount - 1)
    while True:
        G, ecos, socs = _plainSEN(ecoNodes, socNodes, ecoName, socName, nx.DiGraph())
        
        possibleEdges = list(itertools.permutations(itertools.chain(ecos, socs), 2))
        numpy.random.shuffle(possibleEdges)
        
        thisEdgesCount = edgesCount
        if density is None:
            thisEdgesCount = numpy.random.randint(0, edgesCount)
        else:
            thisEdgesCount = int(edgesCount * density)
        
        G.add_edges_from(itertools.islice(possibleEdges, thisEdgesCount))
        yield G