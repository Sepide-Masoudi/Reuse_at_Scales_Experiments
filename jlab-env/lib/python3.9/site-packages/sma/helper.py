# -*- coding: utf-8 -*-

import functools
import networkx as nx
import numpy

def binaryArrayHornersMethod(array : list) -> int:
    """
    transforms the binary number encoded in the given array
    to an integer
    
    :example: binaryArrayHornersMethod([1,0,1]) = 5
    """
    return functools.reduce(lambda x, y: x*2 +y, array)

def multiToWeightedGraph(M : nx.MultiGraph, attr = 'weight') -> nx.Graph:
    """
    Helper function for converting a multigraph into a weighted simple graph with
    edge weights corresponding to the multiplicities of the edges in the multigraph.
    
    Nodal attributes are preserved while edge attributes will be lost. Use the 
    second parameter to set the name of the weight attribute.
    
    :param M: a multigraph
    :param attr: name of the weight attribute
    :returns: a simple graph with weighted edges
    """
    R = nx.Graph()
    R.add_nodes_from(M.nodes(data=True))
    for u,v,data in M.edges(data=True):
        if R.has_edge(u,v):
            R[u][v][attr] += 1
        else:
            R.add_edge(u, v, **{attr : 1})
    return R

def maxEdgeCountMatrix(nVertices : numpy.ndarray) -> numpy.ndarray:
    """
    Returns a matrix containing the maximal possible number of edges in the
    subsystems of a multigraph. The entries of this matrix constitute the upper 
    bounds of the entries of the ``nEdges`` parameter of :py:meth:`sma.randomMultiSENs`.
    
    Let :math:`v_1, \dots, v_n` be the entries of ``nVertices``. Then the entries
    of the returned matrix are
    
    .. math:: 
        
        a_{ij} = \\begin{cases} \\frac12 v_i (v_i-1), & i = j \\\\ v_i v_j, & i < j \\end{cases}.
    
    See also :py:meth:`sma.motifClassMatrix`.
    
    :param nVertices: numbers of vertices per subsystem
    """
    N = len(nVertices)
    matrix = numpy.diag([n*(n-1)//2 for n in nVertices])
    for i in range(N):
        for j in range(i+1, N):
            matrix[i][j] = nVertices[i]*nVertices[j]
    return matrix

def randomEdgeCountMatrix(nVertices : numpy.ndarray) -> numpy.ndarray:
    """
    This function takes the result of :py:meth:`sma.maxEdgeCountMatrix` and a matrix
    with random integer entries less or equal this matrix. It can be used to generate
    a random multilevel SEN with :py:meth:`sma.randomMultiSENs`.
    
    :param nVertices: numbers of vertices per subsystem
    """
    matrix = maxEdgeCountMatrix(nVertices)
    random = numpy.random.random_sample(numpy.shape(matrix))
    return numpy.array(numpy.multiply(matrix, random), dtype=int)

def splitMotifIdentifier(identifier : str) -> tuple:
    """
    Splits a motif identifier into the first part (encoding the pattern and roles 
    of the motif) and the second part (encoding the type of the motif).
    
    For example, ``1:2,2:1[I.C]`` is mapped to the tuple consisting of ``1:2,2:1``
    and ``I.C``.
    
    :param identifier: motif identifier string
    :raises ValueError: in case of parsing problems
    :returns: tuple consisting of first and second part
    """
    if '[' in identifier:
        try:
            first = identifier[:identifier.index('[')]
            second = identifier[identifier.index('[')+1:identifier.index(']')]
        except ValueError:
            raise ValueError("cannot parse invalid motif identifier string \"%s\""\
                             % identifier)
    else:
        first = identifier
        second = None
    return (first, second)
        
def parseMotifIdentifier(identifier : str) -> tuple:
    """
    Parser for motif identifier strings. This function extracts a patterns, roles 
    and motif from a motif identifier string, cf. :py:class:`sma.MultiMotifClassificator`.
    
    A simple motif identifier, e.g. ``1,2[I.C]``, consist of a comma-separated 
    list of integers specifying the pattern of the motif (here, 1 node from one level,
    2 nodes from the other), and of an optional motif name enclosed in brackets.
    
    Motif identifiers can also be used to specify the roles of the levels. An example
    is ``1:1,2:0[I.C]``. The values behind the colons are the roles of the levels.
    
    :param identifier: motif identifier string
    :returns: triple consisting of:
        
        - an arities array
        - a roles array, or ``[]`` if no roles are specified
        - a motif, or ``None`` if no motif is specified
    
    :raises ValueError: in case of parsing problems
    """
    first, second = splitMotifIdentifier(identifier)
    try:
        if ':' in first:
            pairs = first.split(",")
            arities = []
            roles = []
            for p in pairs:
                x, y = p.split(":")
                assert int(x) >= 1, 'value %d as signature entry not allowed' % int(x)
                arities.append(int(x))
                roles.append(int(y))
                assert int(y) >= 0, 'value %d as role not allowed' % int(y)
            return (arities, roles, second)
        else:
            vals = first.split(",")
            return (list(map(int, vals)), [], second)
    except ValueError:
        raise ValueError("cannot parse invalid motif identifier string \"%s\""\
                         % identifier)
    except AssertionError as e:
        raise ValueError("cannot parse invalid motif identifier string \"%s\": %s"\
                         % (identifier, str(e)))

def groupMotifIdentifiers(*motifs : str) -> dict:
    """
    Groups motif identifiers by their heads in a dictionary. For example,
    the list ``1,2[I.A], 2,2[II.B], 1,2[II.B]`` is mapped to 
    ``{'1,2': ['I.A', 'II.B'], '2,2': ['II.B']}``. The returned dict is indexed
    by the heads of the identifiers, the values are lists of motif classes.
    
    :param motifs: list of motif identifiers
    :returns: dict of grouped motif identifiers
    """
    grouped = {}
    for motif in motifs:
        f, s = splitMotifIdentifier(motif)
        if f in grouped:
            grouped[f].append(s)
        else:
            grouped[f] = [s]
    return grouped

def multiSignature(arities : list) -> list:
    """
    Returns the signature of a list of arities. The signature is the list
    of non-zero entries in ascending order. It determines for example the counter 
    function that can be used to count motifs with these arities.
    
    :param arities: list of arities
    :returns: signature
    """
    return sorted(filter(lambda a : a != 0, arities))

def matchPositions(signature : list, 
                   arities : list, 
                   roles : list = []) -> list:
    """
    Position matching is the process in which a signature (e.g. ``1, 2``) is mapped
    to list of positions, i.e. ``sesType`` values in the network (e.g., :py:const:`sma.NODE_TYPE_ECO`,
    :py:const:`sma.NODE_TYPE_SOC` in case of ecological triangles). Optionally,
    a list of roles can be provides. This overwrites the position matching.
    
    :param pattern: the signature
    :param arities: the arities given
    :param roles: optional list of rolls
    :returns: positions
    :raises AssertionError: in case of mismatching signature/arities/roles
    """
    if len(roles) != 0:
        # with roles
        assert len(signature) == len(roles), \
            'signature %s and roles %s must be of the same length' % (str(signature), str(roles))
        if signature == arities:
            return roles
        else:
            arities_positive = list(filter(lambda a : a > 0, arities))
            assert len(arities_positive) == len(signature), \
                'signature %s and positive arities %s must be of the same length'\
                % (str(signature), str(arities_positive))
            prepositions = matchPositions(signature, arities_positive)
            return [roles[i] for i in prepositions]
    else:
        # without roles
        positions = []
        last = {}
        for p in signature:
            if p in last:
                last[p] = arities.index(p, last[p]+1)
            else:
                last[p] = arities.index(p)
            positions.append(last[p])
        return positions

def sortPositions(levels, arities):
    """
    Maps a list of levels and arities to a list of arities ordered according to
    the positions.
    
    For example ``levels = [0, 2, 1]`` and ``arities = [3, 2, 1]`` is mapped 
    to ``[3, 1, 2]``. There are 3 vertices on level 0, 2 vertices on level 2 and
    1 vertex on level 1.
    
    :param levels: list of levels
    :param arities: list of arities
    :returns: list of arities sorted according to positions
    """
    r = [0] * (max(levels)+1)
    for l, a in zip(levels, arities):
        r[l] = a
    return r

def progress_indicator(iterable, 
                       total : int, 
                       width : int = 75, 
                       msg : str = 'Classifying {:,} motifs'):
    """
    Wraps an iterator and shows a progress indicator.

    :param iterable: the iterator
    :param total: total number of items to be processed
    :param width: width of the progress indicator
    :param msg: message to print above progress indicator. Use ``{:,}`` as
        placeholder for number of items.    
    """
    msg = msg.format(total)
    width = max(width, len(msg) + 1)
    print("[", msg, "." * (width - len(msg) - 1), "]")
    print("[ ", end="")
    printed = 0
    print_each = max(total // width, 1)
    for i, x in enumerate(iterable):
        yield x
        if i % print_each == 0 and printed < width:
            print("#", end='', flush=True)
            printed += 1
    if width > printed:
        print("#" * (width - printed), end='')
    print(" ]", flush=True)
