import networkx as nx
import pandas
import csv
import sma.properties

def loadSEN(adjacencyMatrix : str, 
            types : str, 
            delimiter : str = ';',
            create_using : nx.Graph = None) -> nx.Graph:
    """
    Loads a SEN in Madagascar format.
    
    All parameters specifiy file names of the necessary CSV files.
    
    A file stored at ``types`` might look like::
        
        ;soc
        Ocean;0
        Lake;0
        City;1
    
    A file stored at ``adjacencyMatrix`` might look like::
        
        ;Ocean;Lake;City
        Ocean;0;1;0
        Lake;0;0;1
        City;0;0;0
    
    See also :py:meth:`sma.loadDiSEN`.
    
    :param adjacencyMatrix: file name of the CSV file containing the adjacency matrix.
        The first line and the first row are skipped / treated as headings.
    :param types: file name of the CSV file containing the social-ecological type
        encoded as either ``0`` or ``1`` for all nodes
    :param delimiter: CSV delimiter, default is ``;``.
    :param create_using: None or an instance of :py:class:`networkx.Graph` to create
        the network from. Use ``networkx.DiGraph()`` for obtaining a digraph.
    :returns: the graph containing all given data        
    """
    G = create_using if create_using is not None else nx.Graph()
    
    with open(types, 'r') as typesFile:
        reader = csv.reader(typesFile, delimiter = delimiter)
        header = next(reader)[1:]
        sesTypeIndex = header.index('sesType')
        for row in reader:
            if row[0] != '':
                # Assure that sesType is int
                row[sesTypeIndex+1] = int(row[sesTypeIndex+1])
                G.add_node(row[0], **dict(zip(header, row[1:])))
    with open(adjacencyMatrix, 'r') as adjacencyMatrixFile:
        reader = csv.reader(adjacencyMatrixFile, delimiter = delimiter)
        labels = []
        for row in reader:
            if row[0] == '':
                labels = row
            else:
                for i in range(1, len(row)):
                    if int(row[i]) == 1:
                        G.add_edge(row[0], labels[i])
    return G

def loadDiSEN(adjacencyMatrix : str, 
              types : str, 
              delimiter : str = ';',
              create_using : nx.Graph = None) -> nx.DiGraph:
    """
    Synonym of :py:meth:`sma.loadSEN` for loading directed SENs.
    """
    if create_using is None:
        create_using = nx.DiGraph()
    return loadSEN(adjacencyMatrix, types, delimiter, create_using) 

def loadMultifileSEN(
        adjacencyA : str,
        adjacencyB : str,
        adjacencyX : str,
        attributesA : list = [],
        attributesB : list = [],
        attributesX : list = [],
        ) -> nx.Graph:
    """
    Loads a SEN in Woodfire format.

    All parameters specifiy file names of the necessary files.   
    
    :param adjacencyA: adjacency matrix for the social subsystem
    :param adjacencyB: adjacency matrix for the ecological subsystem
    :param adjacencyX: adjacency matrix for the links between the social and the
        ecological subsystems
    :param attributesA: list of file names of CSV files containing nodal attributes
        for the social nodes
    :param attributesB: list of file names of CSV files containing nodal attributes
        for the ecological nodes
    :param attributesX: list of file names of CSV files containing nodal attributes
        for both social and ecological nodes. Social nodes are read first. Thus, their
        attributes must be listed at the beginning of the file
    :returns: the graph containing all given data
    :raises AssertionError: if the dimensions of the files do not match
    """
    adA = pandas.read_csv(adjacencyA, sep=' ', header=None)
    adB = pandas.read_csv(adjacencyB, sep=' ', header=None)
    adX = pandas.read_csv(adjacencyX, sep=' ', header=None)
    
    assert adX.shape == (len(adA), len(adB)), 'X-adjacency matrix must have shape (len soc, len eco)'
    
    lenA = len(adA)
    lenB = len(adB)
    
    # add eco nodes
    G = nx.Graph(adA.values)
    nx.set_node_attributes(G, name='sesType', values={k : sma.properties.NODE_TYPE_SOC for k in range(lenA)})
    
    # add social nodes
    G.add_nodes_from(range(lenA, lenA+lenB), sesType = sma.properties.NODE_TYPE_ECO)
    
    # add social-social edges
    G.add_edges_from(( (lenA + i,lenA + j) for i in range(lenB) for j in range(i) if adB.values[i,j] == True))
    
    # add eco-social edges
    G.add_edges_from(( (i, lenA + j) for i in range(lenA) for j in range(lenB) if adX.values[i,j] == True))
    
    for file in attributesA:
        attr = pandas.read_csv(file, sep='\t', decimal=b',')
        assert len(attr) == lenA, 'attribute matrix in "%s" has illegal shape' % file
        for prop in attr.columns:
            nx.set_node_attributes(G, name=prop, values={k : attr[prop][k] for k in range(lenA)})
    
    for file in attributesB:
        attr = pandas.read_csv(file, sep='\t', decimal=b',')
        assert len(attr) == lenB, 'attribute matrix in "%s" has illegal shape' % file
        for prop in attr.columns:
            nx.set_node_attributes(G, name=prop, values={k + lenA : attr[prop][k] for k in range(lenB)})
    
    for file in attributesX:
        attr = pandas.read_csv(file, sep='\t', decimal=b',')
        assert len(attr) == lenA+lenB, 'attribute matrix in "%s" has illegal shape' % file
        for prop in attr.columns:
            nx.set_node_attributes(G, name=prop, values={k : attr[prop][k] for k in range(lenB+lenA)})
        
    return G

def saveSEN(G : nx.Graph, adjacencyFile : str, attributesFile : str, **kwargs):
    """
    Stores a graph object in two files: a csv adjacency matrix and a csv table 
    containing the nodal attributes. Use kwargs to pass arguments to pandas'
    to_csv facility.
    
    For some reason, panda does not like it when the nodes are of different data
    types. Do not use e.g. integers and string simultaneously to name the nodes.
    
    :param G: the graph to save
    :param adjacencyFile: file name for the adjacency matrix
    :param attributesFile: file name for the nodal attributes (corresponds to
        ``attributesX`` in :py:meth:`sma.loadMultifileSEN`).
    :param kwargs: additional parameters for :py:meth:`pandas.DataFrame.to_csv`.
    """
    ad = nx.to_pandas_adjacency(G, dtype=int)
    ad.to_csv(adjacencyFile, **kwargs)
    
    attr = pandas.DataFrame.from_dict(dict(G.nodes(data=True)), orient='index')
    attr.to_csv(attributesFile, **kwargs)
    
def loadMPNetSEN(file : str) -> nx.Graph:
    """
    Loads a SEN generated by MPNet (version as of Aug 2019), e.g. in its simulation mode. 
    
    This function expects an ``M``-file, e.g. ``thenetwork_Network_M_42.txt`` which
    contains an edge list. Graphs stored in MPNet's input format can be read using
    :py:meth:`sma.loadMultifileSEN`.
    
    MPNet's files are supposed to be Pajek-compatible although they cannot be 
    read by :py:meth:`networkx.read_pajek`. Boxes are translated to social nodes,
    ellipses to ecological nodes.
    
    A file stored at ``file`` might look like::
        
        *vertices 118
        1 "" box ic Blue bc Black
        2 "" box ic Blue bc Black
        ...
        109 "" ellipse ic Red bc Black
        110 "" ellipse ic Red bc Black
        111 "" ellipse ic Red bc Black
        *edges
        1 13 1 c Blue
        1 28 1 c Blue
        1 36 1 c Blue
        ...
    
    :param file: file name of the MPNet graph file
    :returns: the SEN represented by the file
    """
    G = nx.Graph()
    translator = {'box' : sma.properties.NODE_TYPE_SOC, 'ellipse' : sma.properties.NODE_TYPE_ECO}
    with open(file, "r") as f:
        for line in f:
            if line.startswith("*vertices"):
                continue
            if line.startswith("*edges"):
                break
            vals = line.split(" ")
            G.add_node(int(vals[0]), sesType = translator[vals[2]])
        for line in f:
            vals = line.split(" ")
            G.add_edge(int(vals[0]), int(vals[1]))
    return G