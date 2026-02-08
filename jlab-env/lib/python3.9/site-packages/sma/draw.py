import networkx as nx
import sma
import numpy

def _nodeColors(G : nx.Graph, color_map):
    return list(map(lambda x : color_map[x[1]['sesType']], G.nodes(data=True)))

def drawSEN(G : nx.Graph, color_map = sma.COLORS_TYPES, **kwargs) :
    """
    Draws a social-ecological network using :py:meth:`networkx.draw_kamada_kawai`.
    The default drawing behaviour can be overwritten by providing the parameter ``pos``.
    
    :param G: the graph
    :param color_map: a dict mapping the ``sesTypes`` of the nodes to colors,
        default is :py:const:`sma.COLORS_TYPES`.
    :param kwargs: parameters for :py:meth:`networkx.draw_kamada_kawai`
    """
    if 'pos' in kwargs:
        nx.draw(G, 
                  with_labels=True, 
                  node_color=_nodeColors(G, color_map),
                  **kwargs)
    else:
        nx.draw_kamada_kawai(G, 
                      with_labels=True, 
                      node_color=_nodeColors(G, color_map),
                      **kwargs
                      )

def drawGeoSEN(G : nx.Graph, 
               longAttribute : str = 'long', 
               latAttribute : str = 'lat', 
               **kwargs):
    """
    Draws a SEN whose nodes have a location property. :py:meth:`draw_networkx`
    is used as backend.
    
    :param G: the graph
    :param longAttribute: the name of the nodal attribute which contains the longitude
        of the nodes
    :param latAttribute: the name of the nodal attribute which contains the latitude
        of the nodes
    :param kwargs: parameters for :py:meth:`draw_networkx`
    """
    positions = {n : (d[longAttribute], d[latAttribute]) for n, d in G.nodes(data=True)}
    nx.draw_networkx(G, pos=positions, node_color = _nodeColors(G), **kwargs)

def drawMotif(G : nx.Graph, motif : tuple, **kwargs):
    """
    Draws a specific motif in a SEN. 
    
    Example:
    
    .. code :: Python
        
        # let G be some SEN
        motif = sma.exemplifyMotif(G, '1,2[II.C]')
        sma.drawMotif(G, motif)
    
    :param G: the SEN
    :param motif: a motif (tuple of nodes)
    :param kwargs: more parameters for :py:meth:`sma.drawSEN` and 
        :py:meth:`networkx.draw_networkx`.
    """
    H = G.subgraph(motif)
    drawSEN(H, **kwargs)

def layer_layout(G : nx.Graph, scale: float = 5):
    """
    Computes a layout for a SEN which places the nodes of one type on one horizontal
    line. Use it together with :py:meth:`sma.drawSEN`.
    
    .. code-block :: Python
        
        import sma
        # Let G be some SEN
        sma.drawSEN(G, pos=sma.layer_layout(G))
    
    :param G: the SEN
    :param scale: scaling factor
    :returns: layout for :py:meth:`sma.drawSEN`
    """
    nodesCounts = sma.nodesCount(G, array=False)
    maxType = max(nodesCounts.keys())
    source = {k : iter(list(numpy.linspace(0, scale, v))) for k, v in nodesCounts.items()}
    return {node : (next(source[typ]), maxType-typ) for node, typ in G.nodes(data = 'sesType')}

def advanced_layer_layout(G : nx.Graph, space : float = 1):
    """
    Computes a layout for a SEN which places the nodes of one type close to each
    other. Use it together with :py:meth:`sma.drawSEN`.
    
    :param G: the SEN
    :param space: space between the layers
    :returns: layout for :py:meth:`sma.drawSEN`
    """
    nodesCounts = sma.nodesCount(G, array=False)
    shift = numpy.zeros((2))
    positions = {}
    for k, v in nodesCounts.items():
        subgraph = G.subgraph(sma.sesSubgraph(G, k))
        pos = nx.spring_layout(subgraph)
        positions = dict(positions, **{node : coord + shift for node, coord in pos.items()})
        a = numpy.array(list(pos.values()))
        shift[1] -= numpy.max(abs(a[:,1])) + space
    return positions
