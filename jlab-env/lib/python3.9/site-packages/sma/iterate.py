#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sma
import functools, itertools
import networkx as nx

class MotifIterator:
    """
    Motif iterators aim at describing abstact sets of motifs. The concept covers
    4- and 3-motifs as well as sets of nodes (1-motifs). Basically, a set of motifs
    is defined by stating a "source" and "conditions". 
    
    A source is an instance of :py:class:`sma.SourceMotifIterator`. It is an 
    unconditioned iterator which yields all motifs in a network, i.e. all 
    4-motifs or all 3E-motifs. 
    
    A condition is a filter which describes a rule for the motifs in the set, i.e.
    "contains node X" or "contains a node with property Y". Conditions are modeled
    as instances of :py:class:`sma.ConditionMotifIterator` or of its subclasses.
    
    Conditions can be combined using the binary operators & (and) or | (or). Conditions
    and composed conditions can be combined with a source. For example:
    
    "All 4-motifs" & "contains node X" & "contains a node with property Y > Z"
    
    Note, that such a complex term must only contain one source but can contain
    several conditions. Linking a source with conditions by & or | has the same
    effect.
    
    Technically, all classes related to motif iteration are Python iterators. Only
    sources are tangible Python iterators, whereas conditions are filters to these
    iterators. 
    
    Since in R binary operators are not available for complex types, this module
    provides synonymous functions for combining iterators which are callable in 
    R as well as in Python, cf. :py:meth:`sma.motifSet`, :py:meth:`sma.countAnyMotifs`.
    
    Motif iterators can be piped into this module's motif counting and motif
    classifying facilities, cf. :py:meth:`sma.count4Motifs`, :py:meth:`sma.count3Motifs`,
    :py:meth:`sma.countMotifs`.
    
    :param it: an iterator which provides motifs
    """
    def __init__(self, it):
        self.it = it
    def __iter__(self):
        if self.it is None:
            raise TypeError("source must be provided")
        return self
    def __next__(self):
        if self.it is None:
            raise TypeError("source must be provided")
        return self.it.__next__()
    
class ComplexMotifIterator(MotifIterator):
    """
    Motif iterators can be combined to form complex motif iterators describing
    complex sets of motifs with several linked conditions. This class models
    any combination of motif iterators, i.e. two conditions (condition 1 AND 
    condition B) or a source and a condition (all motifs from source which fulfill
    the condition). 
    
    See :py:class:`sma.MotifIterator` for details.
    
    :param G: the graph where the motifs are taken from. This parameter is 
        needed by some conditions which rely i.e. on information about the edges.
    :param source: an iterator which provides the motifs
    :param condition: a function which maps a motif to either True or False,
        stating whether a motif is contained in the set. If None, no condition
        is used (the condition returns always true).
    :param infostr: a string represantation, to be returned by :py:meth:`__str__`
    """
    def __init__(self, G : nx.Graph, source, condition=None, infostr = 'ComplexIterator'):
        self.source = source
        self.G = G
        self.infostr = infostr
        if condition is None:
            self.condition = lambda *x : True
            self.it = self.source
        else:
            self.condition = condition
            if source is None:
                self.it = None
            else:
                self.it = filter(functools.partial(self.condition, self.G), self.source) 
    def _combine(self, other, func, op : str):
        """
        Internal function for combining two :py:class:`ComplexMotifIterator`. 

        :param other: the ComplexMotifIterator to combine this iterator with.
        :param func: a function mapping two booleans to another boolean. The 
            two conditions from this iterator and from other are combined using
            this function, e.g. lambda x,y : x and y for AND.
        :param op: a string indicating the combining operator, e.g. '&' or '|'
        :returns: a ComplexMotifIterator which represents the combination of this
            and other w.r.t. to func.
        """
        if self.source is not None and self.G is not None:
            main = self
            secondary = other
        else:
            main = other
            secondary = self
        return ComplexMotifIterator(
                main.G,
                main.source,
                lambda *x : func(main.condition(*x), secondary.condition(*x)),
                '(%s) %s %s' % (main, op, secondary)
                )
    def __and__(self, other):
        """
        Returns the conjunction of this and other, i.e. a motif iterator which
        models the set of all motifs contained in this set AND in other.
        """
        return self._combine(other, lambda x, y : x and y, '&')
        
    def __or__(self, other):
        """
        Returns the disjunction of this and other, i.e. a motif iterator which
        models the set of all motifs contained in this set OR in other.
        """
        return self._combine(other, lambda x, y : x or y, '|')
    def __str__(self):
        return self.infostr

class ConditionMotifIterator(ComplexMotifIterator):
    """
    Super class of all motif iterators representing a condition (usually without
    providing the source). Note, that an instance of this class cannot be iterated,
    because no source is provided.
    
    :example: "contains node X", cf. :py:class:`sma.hasNode`.
    
    :param condition: function mapping a motif to True or False, stating 
        whether the motif is contained by the set. Note, that the internal 
        format of the motifs depends on the source, cf. the subclasses of
        :py:class:`sma.SourceMotifIterator`.
    """
    def __init__(self, condition):
        super().__init__(None, None, condition)

class SourceMotifIterator(ComplexMotifIterator):
    """
    Representation for a motif source, i.e. a raw, unconditioned set of motifs.
    Examples are the set of all 4-motifs, cf. :py:class:`sma.FourMotifs` and the set
    of all 3-motifs, cf. :py:class:`sma.ThreeEMotifs` for 3E-motif.
    
    SourceMotifIterators not only provide an iterator but also a graph object, which
    is needed by some :py:class:`ConditionMotifIterator` for evaluating for example
    if certain edges exist or not. 
    
    This class might not be used in practice. See its subclass for implementations.
    
    :param G: the graph which this iterator takes motifs from
    :param source: an iterator providing motifs from the graph
    """
    def __init__(self, G : nx.Graph, source : MotifIterator):
        super().__init__(G, source)
    def _combine(self, other : ConditionMotifIterator):
        if isinstance(other, SourceMotifIterator):
            raise TypeError("cannot combine two SourceMotifIterators")
        return ComplexMotifIterator(
                self.G,
                self.source,
                other.condition,
                '%s : %s' % (self, other)
                )
    def __and__(self, other):
        return self._combine(other)
    def __or__(self, other):
        return self._combine(other)

class FourMotifs(SourceMotifIterator):
    """
    Set of all 4-motifs in a graph, cf. :py:meth:`sma.iterate4Motifs`.
    """
    def __init__(self, G : nx.Graph):
        super().__init__(G, sma.iterate4Motifs(G))
    def __str__(self):
        return 'FourMotifs'
        
class OneMotifs(SourceMotifIterator):
    """
    Set of all 1-motifs, i.e. nodes, in a graph. This iterator can be used for
    counting nodes with certain properties:
    """
    def __init__(self, G : nx.Graph):
        super().__init__(G, iter(G.nodes))
    def __str__(self):
        return 'OneMotifs'
    
class ThreeEMotifs(SourceMotifIterator):
    """
    Set of all 3E-motifs in a graph, cf. :py:meth:`sma.iterate3EMotifs`.
    """
    def __init__(self, G : nx.Graph):
        super().__init__(G, sma.iterate3EMotifs(G))
    def __str__(self):
        return 'ThreeEMotifs'
        
class ThreeSMotifs(SourceMotifIterator):
    """
    Set of all 3S-motifs in a graph, cf. :py:meth:`sma.iterate3SMotifs`.
    """
    def __init__(self, G : nx.Graph):
        super().__init__(G, sma.iterate3SMotifs(G))
    def __str__(self):
        return 'ThreeSMotifs'
        
class TwoMotifs(SourceMotifIterator):
    """
    Set of all tuples (s, e) where s is a social node and e is an ecological
    node. Note, that this set is only a superset of the set of all social-ecological
    edges, since not all social and ecological nodes must be connected.
    """
    def __init__(self, G: nx.Graph):
        super().__init__(G, itertools.product(sma.sesSubgraph(G, sma.NODE_TYPE_SOC), 
                         sma.sesSubgraph(G, sma.NODE_TYPE_ECO)))
    def __str__(self):
        return 'TwoMotifs'

class DenseMulti221Motifs(SourceMotifIterator):
    """
    Set of all tuples :math:`(a_1, a_2, b_1, b_2, c)` such that:
        
        - :math:`a_1` and :math:`a_2` are from the upper level (``level0``),
        - :math:`b_1` and :math:`b_2` are from the middle level (``level1``),
        - :math:`c` is from the lower level (``level2``),
        - :math:`b_1` and :math:`b_2` are adjacent to :math:`c`,
    
    and if ``optimize_top_adjacent = True`` additionally:
        
        - :math:`a_1` and :math:`a_2` are adjacent to :math:`c`.
    
    In other words, this motif source contains all *CLASS*.2 and *CLASS*.3 
    (when used with default parameters) or when ``optimize_top_adjacent = True`` 
    all *CLASS*.3 motifs.
    
    This motif source is used by :py:meth:`sma.count221MotifsSparse`.
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper level
    :param level1: ``sesType`` of the middle level
    :param level2: ``sesType`` of the lower level
    :param optimize_top_adjacent: whether the additional condition above should
        be imposed.
    """
    def __init__(self, 
                 G : nx.Graph, 
                 level0, 
                 level1,
                 level2, 
                 optimize_top_adjacent : bool = False):
        if optimize_top_adjacent:
            def __iterate(G):
                for lower in sma.sesSubgraph(G, level2):
                    top = sma.sesSubgraph(G, level0, G[lower]) # top adjacent
                    middle = sma.sesSubgraph(G, level1, G[lower])
                    for mtop, mmiddle in itertools.product(itertools.combinations(top, 2), 
                                                           itertools.combinations(middle, 2)):
                        yield (mtop + mmiddle + (lower,))
        else:
            def __iterate(G):
                for lower in sma.sesSubgraph(G, level2):
                    top = sma.sesSubgraph(G, level0)
                    middle = sma.sesSubgraph(G, level1, G[lower])
                    for mtop, mmiddle in itertools.product(itertools.combinations(top, 2), 
                                                           itertools.combinations(middle, 2)):
                        yield (mtop + mmiddle + (lower,))            
        super().__init__(G, __iterate(G))

class Dense13Motifs(SourceMotifIterator):
    """
    Set of all tuples :math:`(a, b_1, b_2, b_3)` such that:
        
        - :math:`a_1` is from the upper level (``level0``),
        - :math:`b_1, b_2, b_3` are from upper level (``level1``),
        - :math:`a_1` is connected to :math:`b_1, b_3`,
        - :math:`b_2` is connected to :math:`b_1, b_3`
    
    :param G: the SEN
    :param level0: ``sesType`` of the upper level
    :param level1: ``sesType`` of the middle level
    """
    def __init__(self, 
                 G : nx.Graph, 
                 level0, 
                 level1):
        def __iterate(G):
            for a in sma.sesSubgraph(G, level0):
                for b1, b3 in itertools.combinations(sma.sesSubgraph(G, level1, G[a]), 2):
                    for b2 in sma.sesSubgraph(G, level1, G[b1]):
                        if G.has_edge(b2, b3):
                            yield (a, b1, b2, b3)
        super().__init__(G, __iterate(G))

class MultiMotifs(SourceMotifIterator):
    """
    Instances of this class represent a sets of multi-motif.
    A multi-motif is a motif spanning across one or several levels of a SEN. In
    this way it is a generalization of the motifs, cf. :py:class:`sma.FourMotifs`,
    :py:class:`sma.ThreeEMotifs`, etc. A multi-motif is a tuple of tuples. Every
    of its entries represents a tuple of nodes drawn from the associated level of
    the SEN.
    
    The parameters are used to specify how many nodes shall be taken from the levels
    of the SEN. The levels are numbered according to their ``sesType``. Hence the
    first given integer states the number of nodes which shall be taken from level 0,
    the second from level 1 and so on. For example, in SEN with default ``sesType``
    (0: ecological, 1: social) the following two lines are almost equivalent:
        
    .. code-block :: Python
        
        # Let G be some SEN
        motifs1 = sma.MultiMotifs(G, 1, 2)
        list_motifs1 = list(motifs1) # [((123,), (1, 2)), …]
        
        motifs2 = sma.ThreeEMotifs(G)
        list_motifs2 = list(motifs2) # [(123, 1, 2), …]
        
    The fundamental difference between this class and :py:class:`sma.ThreeEMotifs`
    is that the former yields tuples of tuples while the latter produces flat tuples of
    integers. This causes some compatibility problems. You will need to use
    :py:class:`sma.MultiMotifClassificator` for classifying/counting multi-motifs
    instead of e.g. :py:class:`sma.ThreeMotifClassificator`. Set ``flatten = True``
    to make this iterator yield tuples of nodes (not of tuples).
    
    With default parameters this iterator scans through ``arities`` and yields as 
    many nodes as specified from the various subystems. For example, if ``arities = [2, 1, 0]``,
    then the tuples will contain two nodes from level 0, one node from level 1 and
    zero nodes from level 2. However, if ``subsystems`` contains an array, the 
    behaviour is different. Instead of taking :math:`a_i` nodes from level :math:`i`
    where :math:`(a_0, \dots, a_n)` denotes the array in ``arities``, this iterator
    yields :math:`a_i` nodes from level :math:`s_i` where :math:`(s_0, \dots, s_n)` denotes
    the array in ``subsystems``.
    
    See also :py:class:`sma.MultiMotifsNormalized`.
    
    :param G: the SEN
    :param arities: a list of integers representing the numbers of nodes which
        shall be taken from the different levels of the SEN.
    :param flatten: whether the tuples shall be flattened, i.e. whether ``((123,), (1, 2))``
        shall be transformed into ``(123, 1, 2)``.
    :param subsystems: specify the subsystems from which the nodes shall be taken, 
        see above
    """
    def __init__(self, 
                 G: nx.Graph, 
                 *arities : int, 
                 flatten : bool = False,
                 subsystems : list = None):
        self.arities = arities
        if sum(arities) == 0:
            # all arities 0, hence no motifs to yield
            super().__init__(G, [])
        def __source(system, arity):
            if arity == 0:
                return [()]
            return itertools.combinations(sma.sesSubgraph(G, system), arity)
        if subsystems is None:
            subsystems = itertools.count()
        sources = itertools.starmap(__source, zip(subsystems, arities))
        product = itertools.product(*sources)
        if flatten:
            product = map(tuple, map(itertools.chain.from_iterable, product))
        super().__init__(G, product)
    def __str__(self):
        return ('MultiMotifs%s') % str(self.arities)

class MultiMotifsNormalized(MultiMotifs):
    """
    Source for multi-motifs with entries in the order specified by the signature
    of the motif. For example, 3-motifs are always given as tuples (A, B, B)
    regardless of the ``sesType``'s of the levels that A and B come from.
    
    Position matching is used to identify the relavent levels.
    Extends :py:class:`sma.MultiMotifs`.
    
    :param G: the SEN
    :param arities: list of arities
    :param roles: roles, optionally
    :param motif_info: a subclass of :py:class:`sma.MotifInfo`, optionally
    """
    def __init__(self, G: nx.Graph, 
                 *arities : int, 
                 roles = [],
                 motif_info = None):
        if motif_info is None:
            signature  = sma.multiSignature(arities)
            motif_info = sma.motifInfo(signature, G.is_directed())
        positions  = sma.matchPositions(motif_info.signature, arities, roles)
        super().__init__(G, *motif_info.signature, flatten = True, subsystems = positions)

class hasProperty(ConditionMotifIterator):
    """
    Condition for motifs modelling that at least one of the nodes in the motif
    has nodal attribute prop and that rule returns True for this value.
    
    Since it is apparently not possible to transfer lambda/anonymous functions 
    from R to Python using reticulate, some variants of this condition are implemented, 
    cf. :py:class:`sma.hasPropertyGreaterThan` and :py:class:`sma.hasPropertyMatch`.
    
    This condition works for any motif set.
    
    :param prop: the name of the nodal property to look for
    :param rule: a function mapping the value of this attribute to either 
        True or False, stating whether the motif should be contained in the 
        set
    :example: ``hasProperty('EXP', lambda x : x > 2)`` gives all motifs with the
        property that at least one of the nodes has the attribute 'EXP' with
        value greater than 2.
    """
    def __init__(self, prop, rule):
        self.prop = prop
        def _rule(G, motif):
            try:
                for node in motif:
                    if prop in G.nodes[node] and rule(G.nodes[node][prop]):
                        return True
            except TypeError:
                # motif may not be iterable
                if motif in G.nodes and prop in G.nodes[motif] and rule(G.nodes[motif][prop]):
                        return True
            return False
        super().__init__(_rule)
    def __str__(self):
        return 'hasProperty[%s]' % self.prop
        
class hasPropertyGreaterThan(hasProperty):
    """
    Condition for motifs modelling that at least one of the nodes in the motif
    has nodal attribute prop and that its value is greater than threshould.
    
    This condition is equivalent to hasProperty(prop, lambda x : x > threshold).
    
    This condition works for any motif set.
    
    :param prop: the name of the nodal property to look for
    :param threshold: lower boundary for the property's values
    """
    def __init__(self, prop, threshold):
        self.threshold = threshold
        super().__init__(prop, lambda x : x > threshold)
    def __str__(self):
        return 'hasProperty[%s>%d]' % (self.prop, self.threshold)
        
class hasPropertyMatching(hasProperty):
    """
    Condition for motifs modelling that at least one of the nodes in the motif
    has nodal attribute prop and that its value matches value.
    
    This condition is equivalent to hasProperty(prop, lambda x : x == value).
    
    This condition works for any motif set.
    
    :param prop: the name of the nodal property to look for
    :param value: value the nodal property must have
    """
    def __init__(self, prop, value):
        self.value = value
        super().__init__(prop, lambda x : x == value)
    def __str__(self):
        return 'hasProperty[%s==%s]' % (self.prop, self.value)

class hasNode(ConditionMotifIterator):
    """
    Condition for motifs modelling that the motif contains a certain node.
    
    This condition works for any motif set.
    
    :param node: the node to look for
    """
    def __init__(self, node):
        self.node = node
        def _rule(G, motif):
            try:
                return node in motif
            except TypeError: # motif may not be iterable, e.g. OneMotif?
                return node == motif
        super().__init__(_rule)
    def __str__(self):
        return 'hasNode[%s]' % self.node
        
class is4Class(ConditionMotifIterator):
    """
    Condition for 4-motifs modelling that the motif is of certain classes, cf.
    :py:meth:`sma.classify4Motif`.
    
    This condition works only for 4-motifs.
    
    :param typ: classes of the motifs to look for, e.g. 'II.C'.
    """
    def __init__(self, *typ):
        self.typ = typ
        super().__init__(lambda G, motif : sma.classify4Motif(G, motif) in typ)
    def __str__(self):
        return 'has4Class[%s]' % ' or '.join(map(str, self.typ))
        
class is3Class(ConditionMotifIterator):
    """
    Condition for 3-motifs modelling that the motif is of certain classes, cf.
    :py:meth:`sma.classify3Motif`.
    
    This condition works only for 3-motifs.
    
    :param typ: classes of the motifs to look for, e.g. 'II.C'.
    """
    def __init__(self, *typ):
        self.typ = typ
        super().__init__(lambda G, motif : sma.classify3Motif(G, motif) in typ)
    def __str__(self):
        return 'has3Class[%s]' % ' or '.join(map(str, self.typ))

class isClass(ConditionMotifIterator):
    """
    Condition for any sort of motif modelling that a motif is of a certain class.
    Provide a :py:class:`sma.MotifClassificator` as first parameter. The classification
    generated by this classificator will be used to match the given classes.
    
    :param classificator: a :py:class:`sma.MotifClassificator` for classifying
        the motifs
    :param typ: one or several classes
    """
    def __init__(self, classificator : sma.MotifClassificator, *typ):
        self.typ = typ
        self.classificator = classificator
        super().__init__(lambda G, motif: classificator(motif) in typ)
    def __str__(self):
        return 'hasClass[%s=%s]' % (str(self.classificator), ' or '.join(map(str, self.typ)))

class matchesPropertyPattern4Motif(ConditionMotifIterator):
    """
    Condition for 4-motifs modelling that the nodes in the motif have certain 
    properties. 
    
    In contrary to :py:class:`sma.hasProperty` this condition takes
    distinct nodes into account. Thus, rules like "one ecological node has property
    X and `the other` has property Y" can be formulated. If this distinction is 
    not necessary :py:class:`sma.hasProperty` would be the better choice.
    
    The parameters are function mapping a dict of nodal attributes to True or False,
    stating whether the node matches the criterion. All rules have to be matched
    for a motif to be in the set.
    
    This condition may have to complex parameters. 
    See :py:class:`sma.matchesPropertyPattern4MotifGreaterThan` for a more
    straightforward version.
    
    This condition works only for 4-motifs.
    
    :param ruleS1: rule for the first social node
    :param ruleS2: rule for the second social node
    :param ruleS3: rule for the first ecological node
    :param ruleS4: rule for the second ecological node
    """
    def __init__(self, ruleS1, ruleS2, ruleE1, ruleE2):
        def _rule(G, motif):
            s1,s2,e1,e2 = motif
            if not ((ruleS1(G.nodes[s1]) and ruleS2(G.nodes[s2])) or 
                    (ruleS1(G.nodes[s2]) and ruleS2(G.nodes[s1]))):
                return False
            if not ((ruleE1(G.nodes[e1]) and ruleE2(G.nodes[e2])) or 
                    (ruleE1(G.nodes[e2]) and ruleE2(G.nodes[e1]))):
                return False
            return True
        super().__init__(_rule)
        
class matchesPropertyPattern4MotifGreaterThan(matchesPropertyPattern4Motif):
    """
    Condition for 4-motifs modelling that the nodes in the motif have certain
    properties with values greater than a certain threshold.
    
    In contrary to :py:class:`sma.hasPropertyGreaterThan` this condition takes
    distinct nodes into account. Thus, rules like "one ecological node has property
    X and `the other` has property Y" can be formulated. If this distinction is 
    not necessary, :py:class:`sma.hasPropertyGreaterThan` would be the better choice.
    
    All parameters are tuples (k, t) where k is the name of the property to check
    for and t is the threshold.
    
    :example: Possible parameters could be ``propS1 = ('EXP', 2)`` for getting all
        motifs with social nodes with nodal property EXP greater than 2.
    :param propS1: tuple (k, t) as described above for the first social node
    :param propS2: tuple (k, t) as described above for the second social node
    :param propE1: tuple (k, t) as described above for the first ecological node
    :param propE2: tuple (k, t) as described above for the second ecological node
    """
    def __init__(self, propS1 = None, propS2 = None, propE1 = None, propE2 = None):
        self.pattern = [propS1, propS2, propE1, propE2]
        super().__init__(
                ruleS1 = lambda node : propS1 is not None and propS1[0] in node and node[propS1[0]] > propS1[1],
                ruleS2 = lambda node : propS2 is not None and propS2[0] in node and node[propS2[0]] > propS2[1],
                ruleE1 = lambda node : propE1 is not None and propE1[0] in node and node[propE1[0]] > propE1[1],
                ruleE2 = lambda node : propE2 is not None and propE2[0] in node and node[propE2[0]] > propE2[1]
                )
    def __str__(self):
        description = list(map(lambda x: ("%s>%d" % x) if x is not None else '?', self.pattern))
        return 'matchesPattern[%s]' % ','.join(description)
        
        
class matchesPropertyPattern3Motif(ConditionMotifIterator):
    """
    Condition for 3-motifs modelling that the nodes in the motif have certain 
    properties. 
    
    In contrary to :py:class:`sma.hasProperty` this condition takes
    distinct nodes into account. Thus, rules like "one ecological node has property
    X and `the other` has property Y" can be formulated. If this distinction is 
    not necessary :py:class:`sma.hasProperty` would be the better choice.
    
    The parameters are functions mapping a dict of nodal attributes to True or False,
    stating whether the node matches the criterion. All rules have to be matched
    for a motif to be in the set.
    
    This condition may have to complex parameters. 
    See :py:class:`sma.matchesPropertyPattern3MotifGreaterThan` for a more
    straightforward version.
    
    This condition works only for 3-motifs.
    
    :param ruleA: rule for the distinct node (the ecological node in 3E-motifs
         or the social node in 3S-motifs)
    :param ruleB1: rule for the first other node
    :param ruleB2: rule for the second other node
    """
    def __init__(self, ruleA, ruleB1, ruleB2):
        self.rules = [ruleA, ruleB1, ruleB2]
        def _rule(G, motif):
            a, b1, b2 = motif
            if not ruleA(a):
                return False
            if not ((ruleB1(G.nodes[b1]) and ruleB2(G.nodes[b2])) or 
                    (ruleB1(G.nodes[b2]) and ruleB2(G.nodes[b1]))):
                return False
            return True
        super().__init__(_rule)
    def __str__(self):
        return 'matchesPattern[%s]' % ','.join(self.rules)
        
class matchesPropertyPattern3MotifGreaterThan(matchesPropertyPattern3Motif):
    """
    Condition for 3-motifs modelling that the nodes in the motif have certain
    properties with values greater than a certain threshold.
    
    In contrary to :py:class:`sma.hasPropertyGreaterThan` this condition takes
    distinct nodes into account. Thus, rules like "one ecological node has property
    X and `the other` has property Y" can be formulated. If this distinction is 
    not necessary :py:class:`sma.hasPropertyGreaterThan` would be the better choice.
    
    All parameters are tuples (k, t) where k is the name of the property to check
    for and t is the threshold.
    
    :example: Possible parameters could be ``propA = ('EXP', 2)`` for getting all
        motifs with distinct nodes with nodal property EXP greater than 2.
    :param propA: tuple (k, t) as described above for the the distinct node 
        (the ecological node in 3E-motifs or the social node in 3S-motifs)
    :param propB1: tuple (k, t) as described above for the first other node
    :param propB2: tuple (k, t) as described above for the second other node
    """
    def __init__(self, propA = None, propB1 = None, propB2 = None):
        self.pattern = [propA, propB1, propB2]
        super().__init__(
                ruleA  = lambda node : propA is not None and propA[0] in node and node[propA[0]] > propA[1],
                ruleB1 = lambda node : propB1 is not None and propB1[0] in node and node[propB1[0]] > propB1[1],
                ruleB2 = lambda node : propB2 is not None and propB2[0] in node and node[propB2[0]] > propB2[1],
                )
    def __str__(self):
        description = list(map(lambda x: ("%s>%d" % x) if x is not None else '?', self.pattern))
        return 'matchesPattern[%s]' % ','.join(description)