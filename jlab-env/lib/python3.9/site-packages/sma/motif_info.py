#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sma
import inspect, sys
import itertools

class MotifInfo:
    """
    Parent class of all MotifInfo classes. Subclasses contain information about
    motifs, their classificators and counters. The following properties are provided:
        
    :var signature: signature of the motifs
    :var classes: list of names of all motif classes
    :var classes_type: type of the class names, e.g. ``str`` or ``int``
    :var directed: whether the motifs are considered as directed graphs
    :var classificator: subclass of :py:class:`sma.MotifClassificator` for 
          classifying motifs
    :var counter: counting function with signature
        
          ``counter(G, *levels, **kwargs)``
    :var sparse_counter: counting function for sparse graphs with signature
        
          ``sparse_counter(G, *levels, **kwargs)``
    :var expectations: function for computing motif expectations in a
          Erdős-Rényi model
        
          ``expectations(G, *levels, **kwargs)``
    :var variances: function for computing motif variances in a Erdős-Rényi model
        
          ``variances(G, *levels, **kwargs)``
    :var projections: dict containing information about closed/open pairs of motifs,
        i.e. which motif classes belong together when non considering dyads on a 
        specific level of the motif. The dict is indexed by abstract levels (indexes
        of levels in ``signature``). Every entry is a list of tuples of motif class
        names. Each tuple contains first the open and secondly the closed motif.
        See :py:class:`sma.Motif3Info` as an example.
    
    If a certain feature is not implemented, the corresponding value is set to ``None``.
    """
    signature      = []
    classes        = []
    classes_type   = None
    directed       = False
    classificator  = None
    counter        = None
    sparse_counter = None
    expectations   = None
    variances      = None
    projections    = {}
    
def _infoObjects():
    return filter(lambda info: issubclass(info[1], MotifInfo) and info[1] != MotifInfo,
                  inspect.getmembers(sys.modules[__name__], inspect.isclass))
    
def motifInfo(signature : list, directed : bool):
    """
    Returns a subclass of :py:class:`sma.MotifInfo` correponding to the given
    signature. The order of the signature is irrelevant.
    
    :param signature: the signature
    :param directed: whether the motif is a directed graph
    :returns: subclass of :py:class:`sma.MotifInfo`
    :raises NotImplementedError: if no subclass of :py:class:`sma.MotifInfo` is
        available for the given signature
    """
    signature = sorted(signature)
    for name, obj in _infoObjects():
        if directed == obj.directed and signature == sorted(obj.signature):
            return obj
    raise NotImplementedError('%s motifs with signature %s not implemented'\
                              % ('directed' if directed else 'undirected', str(signature)))

def supportedSignatures() -> iter:
    """
    Returns an iterator yielding all tuples of supported signatures together with
    a boolean value indicated whether the corresponding motifs are directed or not.
    
    .. code :: Python
        
        print(list(sma.supportedSignatures()))
        
    
    :returns: iterator yielding all supported signatures.
    """
    return map(lambda x : (x[1].signature, x[1].directed), _infoObjects())

class Motif3Info(MotifInfo):
    """
    3-motifs have signature (1,2). In two-level networks, they are often called
    3E- or 3S-motifs depending on the ``sesType`` of the distinct node.
    """
    signature      = [1, 2]
    classes        = sma.MOTIF3_NAMES
    classes_type   = str
    classificator  = sma.ThreeMotifClassificator
    counter        = sma.count3Motifs
    sparse_counter = sma.count3MotifsSparse
    expectations   = sma.expected3Motifs
    variances      = sma.var3Motifs
    projections    = {1: [('I.A', 'II.A'),
                          ('I.B', 'II.B'),
                          ('I.C', 'II.C')]}

class Motif4Info(MotifInfo):
    """
    4-motifs have signature (2,2). In two-level networks, the first level is usually
    the social level (:py:const:`sma.NODE_TYPE_SOC`) while the second level is
    the ecological level (:py:const:`sma.NODE_TYPE_ECO`).
    """
    signature      = [2, 2]
    classes        = sma.MOTIF4_NAMES
    classes_type   = str
    classificator  = sma.FourMotifClassificator
    counter        = sma.count4Motifs
    sparse_counter = sma.count4MotifsSparse
    expectations   = sma.expected4Motifs
    variances      = sma.var4Motifs
    projections    = {0: [('I.A', 'I.B'),
                          ('I.C', 'I.D'),
                          ('II.A', 'II.B'),
                          ('II.C', 'II.D'),
                          ('III.A', 'III.B'),
                          ('III.C', 'III.D'),
                          ('IV.A', 'IV.B'),
                          ('IV.C', 'IV.D'),
                          ('V.A', 'V.B'),
                          ('V.C', 'V.D'),
                          ('VII.A', 'VI.A'),
                          ('VII.B', 'VI.B'),
                          ('VII.C', 'VI.C'),
                          ('VII.D', 'VI.D')],
                      1: [('I.A', 'I.C'),
                          ('II.A', 'II.C'),
                          ('III.A', 'III.C'),
                          ('IV.A', 'IV.C'),
                          ('V.A', 'V.C'),
                          ('I.B', 'I.D'),
                          ('II.B', 'II.D'),
                          ('III.B', 'III.D'),
                          ('IV.B', 'IV.D'),
                          ('V.B', 'V.D'),
                          ('VI.A', 'VI.B'),
                          ('VI.C', 'VI.D'),
                          ('VII.A', 'VII.B'),
                          ('VII.C', 'VII.D')]}
    
class Motif23Info(MotifInfo):
    """
    Signature (2,3). Not all motifs with this signature are classified yet. Visit
    the motif zoo for details.
    """
    signature      = [2, 3]
    classes        = [-1, 1]
    classes_type   = int
    classificator  = sma.TwoThreeMotifClassificator
    counter        = None
    sparse_counter = None
    expectations   = None
    variances      = None
    projections    = None
    
class Motif13Info(MotifInfo):
    """
    Signature (1,3). Not all motifs with this signature are classified yet. Visit
    the motif zoo for details.
    """
    signature      = [1, 3]
    classes        = [-1, 1]
    classes_type   = int
    classificator  = sma.OneThreeMotifClassificator
    counter        = None
    sparse_counter = sma.count13MotifsSparse
    expectations   = None
    variances      = None
    projections    = None

class Motif111Info(MotifInfo):
    """
    Signature (1,1,1).
    """
    signature      = [1, 1, 1]
    classes        = [0, 1, 2, 3, 4, 5, 6, 7]
    classes_type   = int
    classificator  = sma.Multi111MotifClassificator
    counter        = None
    sparse_counter = None
    expectations   = sma.expected111Motifs
    variances      = None

class Motif121Info(MotifInfo):
    """
    Signature (1,2,1). Not all motifs with this signature are classified yet. Visit
    the motif zoo for details.
    """
    signature      = [1, 2, 1]
    classes        = [-1, 1, 2, 3, 4]
    classes_type   = int
    classificator  = sma.Multi121MotifClassificator
    counter        = None
    sparse_counter = sma.count121MotifsSparse
    expectations   = sma.expected121Motifs
    variances      = None

class Motif221Info(MotifInfo):
    """
    Signature (2,2,1). Not all motifs with this signature are classified yet. Visit
    the motif zoo for details.
    """
    signature      = [2, 2, 1]
    classes        = ['Unclassified'] + list(map(lambda x : '%s.%d' % x, 
                     itertools.product(sma.MOTIF4_NAMES, [0,1,2,3])))
    classes_type   = str
    classificator  = sma.Multi221MotifClassificator
    counter        = None
    sparse_counter = sma.count221MotifsSparse
    expectations   = sma.expected221Motifs
    variances      = None

class Motif222Info(MotifInfo):
    """
    Signature (2,2,2). Not all motifs with this signature are classified yet. Visit
    the motif zoo for details.
    """
    signature      = [2, 2, 2]
    classes        = [-1, 1, 2, 3, 4]
    classes_type   = int
    classificator  = sma.Multi222MotifClassificator
    counter        = None
    sparse_counter = sma.count222MotifsSparse
    expectations   = sma.expected222Motifs
    variances      = None

class Motif2Info(MotifInfo):
    """
    2-motifs are similar to (1,1)-motifs (cf. :py:class:`sma.Motif11Info`). They
    have signature (2), so consist of two nodes on the same level.
    """
    signature      = [2]
    classes        = [0, 1]
    classes_type   = int
    classificator  = sma.TwoMotifClassificator
    counter        = sma.count2pMotifs
    sparse_counter = None
    expectations   = None
    variances      = None

class Motif11Info(MotifInfo):
    """
    (1,1)-motifs are similar to 2-motifs (cf. :py:class:`sma.Motif2Info`). They
    have signature (1,1), so consist of two nodes on different levels.
    """
    signature      = [1, 1]
    classes        = [0, 1]
    classes_type   = int
    classificator  = sma.TwoMotifClassificator
    counter        = None
    sparse_counter = None
    expectations   = None
    variances      = None
    
class Motif3pInfo(MotifInfo):
    """
    3p-motifs have signature (3). So they consist of three nodes on the same level.
    """
    signature      = [3]
    classes        = [0, 1, 2, 3]
    classes_type   = int
    classificator  = sma.ThreePMotifClassificator
    counter        = sma.count3pMotifsLinalg
    sparse_counter = None
    expectations   = None
    variances      = None

class Motif1Info(MotifInfo):
    """
    1-motifs are most boring. They contain just a single node.
    See also :py:class:`sma.DiMotif1Info`.
    """
    signature      = [1]
    classes        = [1]
    classes_type   = int
    classificator  = sma.OneMotifClassificator
    counter        = None
    sparse_counter = None
    expectations   = None
    variances      = None

class DiMotif1Info(MotifInfo):
    """
    Directed 1-motifs are most boring. They contain just a single node.
    See also :py:class:`sma.Motif1Info`.
    """
    signature      = [1]
    classes        = [1]
    classes_type   = int
    directed       = True
    classificator  = sma.OneMotifClassificator
    counter        = None
    sparse_counter = None
    expectations   = None
    variances      = None

class DiMotif11Info(MotifInfo):
    """
    Directed motifs with signature (1, 1), i.e. with two distinct nodes. See also
    :py:class:`sma.DiMotif2Info`.
    """
    signature      = [1, 1]
    classes        = [0, 1, 2, 3]
    directed       = True
    classes_type   = int
    classificator  = sma.DiMotif11Classificator
    counter        = None
    sparse_counter = None
    expectations   = None
    variances      = None

class DiMotif2Info(MotifInfo):
    """
    Directed motifs with signature (2). See also :py:class:`sma.DiMotif11Info`.
    """
    signature      = [2]
    classes        = [0, 1, 2]
    directed       = True
    classes_type   = int
    classificator  = sma.DiMotif2Classificator
    counter        = None
    sparse_counter = None
    expectations   = None
    variances      = None

class DiMotif12Info(MotifInfo):
    """
    Directed motifs with signature (1,2).
    """
    signature      = [1, 2]
    classes        = ["I.A", 
                      "I.B.1", "I.B.2", "I.B.3",
                      "I.C.1", "I.C.2", "I.C.3", "I.C.4", "I.C.5", "I.C.6",
                      "II.A",
                      "II.B.1", "II.B.2", "II.B.3", "II.B.4", "II.B.5", "II.B.6",
                      "II.C.1", "II.C.2", "II.C.3", "II.C.4", "II.C.5", "II.C.6",
                      "II.C.7", "II.C.8", "II.C.9",
                      "III.A", 
                      "III.B.1", "III.B.2", "III.B.3",
                      "III.C.1", "III.C.2", "III.C.3", "III.C.4", "III.C.5", "III.C.6"]
    directed       = True
    classes_type   = str
    classificator  = sma.DiMotif12Classificator
    counter        = None
    sparse_counter = None
    expectations   = None
    variances      = None

class DiMotif22Info(MotifInfo):
    """
    Directed motifs with signature (2,2).
    """
    signature      = [2, 2]
    classes        = sma.DIMOTIF22_NAMES
    directed       = True
    classes_type   = str
    classificator  = sma.DiMotif22Classificator
    counter        = None
    sparse_counter = None
    expectations   = None
    variances      = None


