# -*- coding: utf-8 -*-

import numpy

NODE_TYPE_SOC = 1
NODE_TYPE_ECO = 0 

EDGE_TYPE_SOC_SOC = 2
EDGE_TYPE_ECO_SOC = 1
EDGE_TYPE_ECO_ECO = 0

MOTIF4_NAMES = ['I.A', 'I.B', 'I.C', 'I.D', 'II.A', 'II.B', 'II.C', 'II.D', 
                'III.A', 'III.B', 'III.C', 'III.D', 'IV.A', 'IV.B', 'IV.C', 'IV.D', 
                'V.A', 'V.B', 'V.C', 'V.D', 'VI.A', 'VI.B', 'VI.C', 'VI.D', 
                'VII.A', 'VII.B', 'VII.C', 'VII.D']
MOTIF3_NAMES = ['I.A', 'I.B', 'I.C', 'II.A', 'II.B', 'II.C']

COLORS_TYPES = {
                NODE_TYPE_ECO : 'green', 
                NODE_TYPE_SOC : 'red',
                2 : 'c', 
                3 : 'm', 
                4 : 'y', 
                5 : 'k', 
                6 : 'w'
                }

MULTI_DEFAULT_NAMES = ['Lake', 'Town', 'Issue', 'System', 'Entity', 'Item', 'Universe']

MOTIF3_EDGES = numpy.array([[0,0],[0,1],[0,2],[1,0],[1,1],[1,2]])

MOTIF4_EDGES = numpy.array([[0,2,0],
                         [1,2,0],
                         [0,2,1],
                         [1,2,1],
                         [0,2,0],
                         [1,2,0],
                         [0,2,1],
                         [1,2,1],
                         [0,4,0],
                         [1,4,0],
                         [0,4,1],
                         [1,4,1],
                         [0,0,0],
                         [1,0,0],
                         [0,0,1],
                         [1,0,1],
                         [0,3,0],
                         [1,3,0],
                         [0,3,1],
                         [1,3,1],
                         [1,1,0],
                         [1,1,1],
                         [1,2,0],
                         [1,2,1],
                         [0,1,0],
                         [0,1,1],
                         [0,2,0],
                         [0,2,1]])

MOTIF4_SYMMETRIES = numpy.array([2, 2, 2, 2, 
                                 2, 2, 2, 2, 
                                 4, 4, 4, 4, 
                                 1, 1, 1, 1, # sparse motifs IV.A-IV.D
                                 3, 3, 3, 3, 
                                 1, 1, 2, 2, 
                                 1, 1, 2, 2])

MOTIF4_AUT = numpy.array([2, 2, 2, 2, 
                          2, 2, 2, 2, 
                          1, 1, 1, 1, 
                          1, 1, 1, 1, # sparse motifs IV.A-IV.D
                          4, 4, 4, 4, 
                          4, 4, 2, 2, 
                          4, 4, 2, 2])
MOTIF3_AUT = numpy.array([1, 2, 1, 1, 2, 1])

# models for random baselines
MODEL_ERDOS_RENYI     = 'erdos_renyi'
MODEL_ACTORS_CHOICE   = 'actors_choice'
MODEL_FIXED_DENSITIES = 'fixed_densities'

def binaryCodeToClass4Motifs(digits : int) -> str:
    """
    Classifies 4-motifs according to 
    Ö. Bodin, M. Tengö: Disentangling intangible social–ecological systems 
    Global Environmental Change 22 (2012) 430–439
    http://dx.doi.org/10.1016/j.gloenvcha.2012.01.005
    
    :param digits: binary code of the motif as described in the paper
    :returns: string code 'I.A' to 'VII.D'
    :raises ValueError: if the given digits are not in the required range
    """
    if digits == 0b000000:  return 'IV.A'
    if(digits == 0b000100 or
       digits == 0b010000 or
       digits == 0b000001 or
       digits == 0b000010): return 'VII.A'
    if digits == 0b001000:  return 'IV.C'
    if digits == 0b100000:  return 'IV.B'
    if(digits == 0b000101 or
       digits == 0b010010): return 'II.A'
    if(digits == 0b000110 or
       digits == 0b010001): return 'VII.C'
    if(digits == 0b010100 or
       digits == 0b000011): return 'I.A'
    if(digits == 0b001100 or
       digits == 0b011000 or
       digits == 0b001010 or
       digits == 0b001001): return 'VII.B'
    if(digits == 0b100100 or
       digits == 0b100001 or
       digits == 0b100010 or
       digits == 0b110000): return 'VI.A'
    if digits == 0b101000:  return 'IV.D'
    if(digits == 0b001101 or
       digits == 0b011010): return 'II.C'
    if(digits == 0b100101 or
       digits == 0b110010): return 'II.B'
    if(digits == 0b101100 or
       digits == 0b111000 or
       digits == 0b101001 or
       digits == 0b101010): return 'VI.B'
    if(digits == 0b001110 or
       digits == 0b011001): return 'VII.D'
    if(digits == 0b010110 or
       digits == 0b010011 or
       digits == 0b010101 or
       digits == 0b000111): return 'V.A'
    if(digits == 0b100110 or
       digits == 0b110001): return 'VI.C'
    if(digits == 0b011100 or
       digits == 0b001011): return 'I.C'
    if(digits == 0b110100 or
       digits == 0b100011): return 'I.B'
    if digits == 0b010111:  return 'III.A'
    if(digits == 0b101101 or
       digits == 0b111010): return 'II.D'
    if(digits == 0b011110 or
       digits == 0b011011 or
       digits == 0b011101 or
       digits == 0b001111): return 'V.C'
    if(digits == 0b101110 or
       digits == 0b111001): return 'VI.D'
    if(digits == 0b110110 or
       digits == 0b110011 or
       digits == 0b110101 or
       digits == 0b100111): return 'V.B'
    if(digits == 0b111100 or
       digits == 0b101011): return 'I.D'
    if digits == 0b011111:  return 'III.C'
    if digits == 0b110111:  return 'III.B'
    if(digits == 0b111110 or
       digits == 0b111101 or
       digits == 0b101111 or
       digits == 0b111011): return 'V.D'
    if digits == 0b111111:  return 'III.D'
    raise ValueError('cannot decode digits {0:b} for 4-motif'.format(digits))

def binaryCodeToClass3Motifs(digits : int) -> str:
    """
    Classifies 3-motifs according to the following scheme: A 3-motif consists of either
    one social and two ecological nodes or one ecological and two social nodes. Thus, 
    one node can be considered distinct from the two other nodes. Let's call this node
    :math:`a` and the other two nodes :math:`b_1` and :math:`b_2`. 
    The following classes occur (listing undirected edges):
        
    class I: without edge :math:`(b_1,b_2)`:
        - I.A: no edges,
        - I.B: either :math:`(a,b_1)` or :math:`(a,b_2)`,
        - I.C: both :math:`(a,b_1)` and :math:`(a,b_2)`.
    class II: with edge :math:`(b_1,b_2)`:
        - II.A: :math:`(b_1,b_2)`,
        - II.B: :math:`(b_1,b_2)` and either :math:`(a,b_1)` or :math:`(a,b_2)`,
        - II.C: :math:`(b_1,b_2)` and both :math:`(a,b_1)` and :math:`(a,b_2)`.
    
    :param digits: binary code of the motif as described above
    :returns: string code 'I.A' to 'VII.D'
    :raises ValueError: if the given digits are not in the required range
    """ 
    digits1 = digits // 4
    digits2 = digits % 4
    
    cl1 = ''
    if digits1 == 0:
        cl1 = 'I'
    elif digits1 == 1:
        cl1 = 'II'
    else:
        raise ValueError('cannot decode digits {0:b} for 3-motif'.format(digits))
    
    cl2 = ''
    if digits2 == 0b00:
        cl2 = 'A'
    elif digits2 == 0b11:
        cl2 = 'C'
    else:
        cl2 = 'B'
    return cl1 + '.' + cl2

DIMOTIF22_NAMES = ['I.A', 'I.B.1', 'I.B.2', 'I.B.3', 'I.C.1', 'I.C.2', 
                    'I.C.3', 'I.C.4', 'I.C.5', 'I.C.6', 'I.D.1', 
                    'I.D.2', 'I.D.3', 'I.D.4', 'I.D.5', 'I.D.6', 
                    'I.E.1', 'I.E.2', 'I.E.3', 'I.E.4', 'I.E.5', 
                    'I.E.6', 'I.F.ddd', 'I.F.ddu', 'I.F.ddb', 'I.F.dud', 
                    'I.F.duu', 'I.F.dub', 'I.F.dbd', 'I.F.dbu', 'I.F.dbb', 
                    'I.F.udd', 'I.F.udu', 'I.F.udb', 'I.F.uud', 'I.F.uuu', 
                    'I.F.uub', 'I.F.ubd', 'I.F.ubu', 'I.F.ubb', 'I.F.bdd', 
                    'I.F.bdu', 'I.F.bdb', 'I.F.bud', 'I.F.buu', 'I.F.bub', 
                    'I.F.bbd', 'I.F.bbu', 'I.F.bbb', 'I.Ga.A', 'I.Ga.B', 
                    'I.Ga.C', 'I.Ga.D', 'I.Ga.E', 'I.Ga.F', 'I.Ga.G', 
                    'I.Gb.ddd', 'I.Gb.ddu', 'I.Gb.dud', 'I.Gb.duu', 'I.Gb.udd', 
                    'I.Gb.udu', 'I.Gb.uud', 'I.Gb.uuu', 'I.Gc.1', 'I.Gc.2', 
                    'I.Gc.3', 'I.Gd.1', 'I.Gd.2', 'I.Gd.3', 'I.Ge.1', 
                    'I.Ge.2', 'I.Ge.4', 'I.Gf.1', 'I.Gf.2', 'I.Gg', 
                    'II.AA', 'II.AB1', 'II.AB2', 'II.AB3', 'II.AC1', 
                    'II.AC2', 'II.AC3', 'II.AC4', 'II.AC5', 'II.AC6', 
                    'II.B1A', 'II.B1B1', 'II.B1B2', 'II.B1B3', 'II.B1C1', 
                    'II.B1C2', 'II.B1C3', 'II.B1C4', 'II.B1C5', 'II.B1C6', 
                    'II.B2A', 'II.B2B1', 'II.B2B2', 'II.B2B3', 'II.B2C1', 
                    'II.B2C2', 'II.B2C3', 'II.B2C4', 'II.B2C5', 'II.B2C6', 
                    'II.B3A', 'II.B3B1', 'II.B3B2', 'II.B3B3', 'II.B3C1', 
                    'II.B3C2', 'II.B3C3', 'II.B3C4', 'II.B3C5', 'II.B3C6', 
                    'II.C1A', 'II.C1B1', 'II.C1B2', 'II.C1B3', 'II.C1C1', 
                    'II.C1C2', 'II.C1C3', 'II.C1C4', 'II.C1C5', 'II.C1C6', 
                    'II.C2A', 'II.C2B1', 'II.C2B2', 'II.C2B3', 'II.C2C1', 
                    'II.C2C2', 'II.C2C3', 'II.C2C4', 'II.C2C5', 'II.C2C6', 
                    'II.C3A', 'II.C3B1', 'II.C3B2', 'II.C3B3', 'II.C3C1', 
                    'II.C3C2', 'II.C3C3', 'II.C3C4', 'II.C3C5', 'II.C3C6', 
                    'II.C4A', 'II.C4B1', 'II.C4B2', 'II.C4B3', 'II.C4C1', 
                    'II.C4C2', 'II.C4C3', 'II.C4C4', 'II.C4C5', 'II.C4C6', 
                    'II.C5A', 'II.C5B1', 'II.C5B2', 'II.C5B3', 'II.C5C1', 
                    'II.C5C2', 'II.C5C3', 'II.C5C4', 'II.C5C5', 'II.C5C6', 
                    'II.C6A', 'II.C6B1', 'II.C6B2', 'II.C6B3', 'II.C6C1', 
                    'II.C6C2', 'II.C6C3', 'II.C6C4', 'II.C6C5', 'II.C6C6', 
                    'III.A', 'III.B.1', 'III.B.2', 'III.B.3', 'III.C.1', 
                    'III.C.2', 'III.C.3', 'III.C.4', 'III.C.5', 'III.C.6', 
                    'III.D.1', 'III.D.2', 'III.D.3', 'III.D.4', 'III.D.5', 
                    'III.D.6', 'III.E.1', 'III.E.2', 'III.E.3', 'III.E.4', 
                    'III.E.5', 'III.E.6', 'III.F.ddd', 'III.F.ddu', 'III.F.ddb', 
                    'III.F.dud', 'III.F.duu', 'III.F.dub', 'III.F.dbd', 'III.F.dbu', 
                    'III.F.dbb', 'III.F.udd', 'III.F.udu', 'III.F.udb', 'III.F.uud', 
                    'III.F.uuu', 'III.F.uub', 'III.F.ubd', 'III.F.ubu', 'III.F.ubb', 
                    'III.F.bdd', 'III.F.bdu', 'III.F.bdb', 'III.F.bud', 'III.F.buu', 
                    'III.F.bub', 'III.F.bbd', 'III.F.bbu', 'III.F.bbb', 'III.Ga.A', 
                    'III.Ga.B', 'III.Ga.C', 'III.Ga.D', 'III.Ga.E', 'III.Ga.F', 
                    'III.Ga.G', 'III.Gb.ddd', 'III.Gb.ddu', 'III.Gb.dud', 'III.Gb.duu', 
                    'III.Gb.udd', 'III.Gb.udu', 'III.Gb.uud', 'III.Gb.uuu', 'III.Gc.1', 
                    'III.Gc.2', 'III.Gc.3', 'III.Gd.1', 'III.Gd.2', 'III.Gd.3', 
                    'III.Ge.1', 'III.Ge.2', 'III.Ge.4', 'III.Gf.1', 'III.Gf.2', 
                    'III.Gg', 'IV.AA', 'IV.AB1', 'IV.AB2', 'IV.AB3', 
                    'IV.AC1', 'IV.AC2', 'IV.AC3', 'IV.AC4', 'IV.AC5', 
                    'IV.AC6', 'IV.B1A', 'IV.B1B1', 'IV.B1B2', 'IV.B1B3', 
                    'IV.B1C1', 'IV.B1C2', 'IV.B1C3', 'IV.B1C4', 'IV.B1C5', 
                    'IV.B1C6', 'IV.B2A', 'IV.B2B1', 'IV.B2B2', 'IV.B2B3', 
                    'IV.B2C1', 'IV.B2C2', 'IV.B2C3', 'IV.B2C4', 'IV.B2C5', 
                    'IV.B2C6', 'IV.B3A', 'IV.B3B1', 'IV.B3B2', 'IV.B3B3', 
                    'IV.B3C1', 'IV.B3C2', 'IV.B3C3', 'IV.B3C4', 'IV.B3C5', 
                    'IV.B3C6', 'IV.C1A', 'IV.C1B1', 'IV.C1B2', 'IV.C1B3', 
                    'IV.C1C1', 'IV.C1C2', 'IV.C1C3', 'IV.C1C4', 'IV.C1C5', 
                    'IV.C1C6', 'IV.C2A', 'IV.C2B1', 'IV.C2B2', 'IV.C2B3', 
                    'IV.C2C1', 'IV.C2C2', 'IV.C2C3', 'IV.C2C4', 'IV.C2C5', 
                    'IV.C2C6', 'IV.C3A', 'IV.C3B1', 'IV.C3B2', 'IV.C3B3', 
                    'IV.C3C1', 'IV.C3C2', 'IV.C3C3', 'IV.C3C4', 'IV.C3C5', 
                    'IV.C3C6', 'IV.C4A', 'IV.C4B1', 'IV.C4B2', 'IV.C4B3', 
                    'IV.C4C1', 'IV.C4C2', 'IV.C4C3', 'IV.C4C4', 'IV.C4C5', 
                    'IV.C4C6', 'IV.C5A', 'IV.C5B1', 'IV.C5B2', 'IV.C5B3', 
                    'IV.C5C1', 'IV.C5C2', 'IV.C5C3', 'IV.C5C4', 'IV.C5C5', 
                    'IV.C5C6', 'IV.C6A', 'IV.C6B1', 'IV.C6B2', 'IV.C6B3', 
                    'IV.C6C1', 'IV.C6C2', 'IV.C6C3', 'IV.C6C4', 'IV.C6C5', 
                    'IV.C6C6', 'V.nnnn', 'V.nnnd', 'V.nnnu', 'V.nnnb', 
                    'V.nndn', 'V.nndd', 'V.nndu', 'V.nndb', 'V.nnun', 
                    'V.nnud', 'V.nnuu', 'V.nnub', 'V.nnbn', 'V.nnbd', 
                    'V.nnbu', 'V.nnbb', 'V.ndnn', 'V.ndnd', 'V.ndnu', 
                    'V.ndnb', 'V.nddn', 'V.nddd', 'V.nddu', 'V.nddb', 
                    'V.ndun', 'V.ndud', 'V.nduu', 'V.ndub', 'V.ndbn', 
                    'V.ndbd', 'V.ndbu', 'V.ndbb', 'V.nunn', 'V.nund', 
                    'V.nunu', 'V.nunb', 'V.nudn', 'V.nudd', 'V.nudu', 
                    'V.nudb', 'V.nuun', 'V.nuud', 'V.nuuu', 'V.nuub', 
                    'V.nubn', 'V.nubd', 'V.nubu', 'V.nubb', 'V.nbnn', 
                    'V.nbnd', 'V.nbnu', 'V.nbnb', 'V.nbdn', 'V.nbdd', 
                    'V.nbdu', 'V.nbdb', 'V.nbun', 'V.nbud', 'V.nbuu', 
                    'V.nbub', 'V.nbbn', 'V.nbbd', 'V.nbbu', 'V.nbbb', 
                    'V.dnnn', 'V.dnnd', 'V.dnnu', 'V.dnnb', 'V.dndn', 
                    'V.dndd', 'V.dndu', 'V.dndb', 'V.dnun', 'V.dnud', 
                    'V.dnuu', 'V.dnub', 'V.dnbn', 'V.dnbd', 'V.dnbu', 
                    'V.dnbb', 'V.ddnn', 'V.ddnd', 'V.ddnu', 'V.ddnb', 
                    'V.dddn', 'V.dddd', 'V.dddu', 'V.dddb', 'V.ddun', 
                    'V.ddud', 'V.dduu', 'V.ddub', 'V.ddbn', 'V.ddbd', 
                    'V.ddbu', 'V.ddbb', 'V.dunn', 'V.dund', 'V.dunu', 
                    'V.dunb', 'V.dudn', 'V.dudd', 'V.dudu', 'V.dudb', 
                    'V.duun', 'V.duud', 'V.duuu', 'V.duub', 'V.dubn', 
                    'V.dubd', 'V.dubu', 'V.dubb', 'V.dbnn', 'V.dbnd', 
                    'V.dbnu', 'V.dbnb', 'V.dbdn', 'V.dbdd', 'V.dbdu', 
                    'V.dbdb', 'V.dbun', 'V.dbud', 'V.dbuu', 'V.dbub', 
                    'V.dbbn', 'V.dbbd', 'V.dbbu', 'V.dbbb', 'V.unnn', 
                    'V.unnd', 'V.unnu', 'V.unnb', 'V.undn', 'V.undd', 
                    'V.undu', 'V.undb', 'V.unun', 'V.unud', 'V.unuu', 
                    'V.unub', 'V.unbn', 'V.unbd', 'V.unbu', 'V.unbb', 
                    'V.udnn', 'V.udnd', 'V.udnu', 'V.udnb', 'V.uddn', 
                    'V.uddd', 'V.uddu', 'V.uddb', 'V.udun', 'V.udud', 
                    'V.uduu', 'V.udub', 'V.udbn', 'V.udbd', 'V.udbu', 
                    'V.udbb', 'V.uunn', 'V.uund', 'V.uunu', 'V.uunb', 
                    'V.uudn', 'V.uudd', 'V.uudu', 'V.uudb', 'V.uuun', 
                    'V.uuud', 'V.uuuu', 'V.uuub', 'V.uubn', 'V.uubd', 
                    'V.uubu', 'V.uubb', 'V.ubnn', 'V.ubnd', 'V.ubnu', 
                    'V.ubnb', 'V.ubdn', 'V.ubdd', 'V.ubdu', 'V.ubdb', 
                    'V.ubun', 'V.ubud', 'V.ubuu', 'V.ubub', 'V.ubbn', 
                    'V.ubbd', 'V.ubbu', 'V.ubbb', 'V.bnnn', 'V.bnnd', 
                    'V.bnnu', 'V.bnnb', 'V.bndn', 'V.bndd', 'V.bndu', 
                    'V.bndb', 'V.bnun', 'V.bnud', 'V.bnuu', 'V.bnub', 
                    'V.bnbn', 'V.bnbd', 'V.bnbu', 'V.bnbb', 'V.bdnn', 
                    'V.bdnd', 'V.bdnu', 'V.bdnb', 'V.bddn', 'V.bddd', 
                    'V.bddu', 'V.bddb', 'V.bdun', 'V.bdud', 'V.bduu', 
                    'V.bdub', 'V.bdbn', 'V.bdbd', 'V.bdbu', 'V.bdbb', 
                    'V.bunn', 'V.bund', 'V.bunu', 'V.bunb', 'V.budn', 
                    'V.budd', 'V.budu', 'V.budb', 'V.buun', 'V.buud', 
                    'V.buuu', 'V.buub', 'V.bubn', 'V.bubd', 'V.bubu', 
                    'V.bubb', 'V.bbnn', 'V.bbnd', 'V.bbnu', 'V.bbnb', 
                    'V.bbdn', 'V.bbdd', 'V.bbdu', 'V.bbdb', 'V.bbun', 
                    'V.bbud', 'V.bbuu', 'V.bbub', 'V.bbbn', 'V.bbbd', 
                    'V.bbbu', 'V.bbbb', 'VI.AA', 'VI.AB1', 'VI.AB2', 
                    'VI.AB3', 'VI.AC1', 'VI.AC2', 'VI.AC3', 'VI.AC4', 
                    'VI.AC5', 'VI.AC6', 'VI.B1A', 'VI.B1B1', 'VI.B1B2', 
                    'VI.B1B3', 'VI.B1C1', 'VI.B1C2', 'VI.B1C3', 'VI.B1C4', 
                    'VI.B1C5', 'VI.B1C6', 'VI.B2A', 'VI.B2B1', 'VI.B2B2', 
                    'VI.B2B3', 'VI.B2C1', 'VI.B2C2', 'VI.B2C3', 'VI.B2C4', 
                    'VI.B2C5', 'VI.B2C6', 'VI.B3A', 'VI.B3B1', 'VI.B3B2', 
                    'VI.B3B3', 'VI.B3C1', 'VI.B3C2', 'VI.B3C3', 'VI.B3C4', 
                    'VI.B3C5', 'VI.B3C6', 'VI.C1A', 'VI.C1B1', 'VI.C1B2', 
                    'VI.C1B3', 'VI.C1C1', 'VI.C1C2', 'VI.C1C3', 'VI.C1C4', 
                    'VI.C1C5', 'VI.C1C6', 'VI.C2A', 'VI.C2B1', 'VI.C2B2', 
                    'VI.C2B3', 'VI.C2C1', 'VI.C2C2', 'VI.C2C3', 'VI.C2C4', 
                    'VI.C2C5', 'VI.C2C6', 'VI.C3A', 'VI.C3B1', 'VI.C3B2', 
                    'VI.C3B3', 'VI.C3C1', 'VI.C3C2', 'VI.C3C3', 'VI.C3C4', 
                    'VI.C3C5', 'VI.C3C6', 'VI.C4A', 'VI.C4B1', 'VI.C4B2', 
                    'VI.C4B3', 'VI.C4C1', 'VI.C4C2', 'VI.C4C3', 'VI.C4C4', 
                    'VI.C4C5', 'VI.C4C6', 'VI.C5A', 'VI.C5B1', 'VI.C5B2', 
                    'VI.C5B3', 'VI.C5C1', 'VI.C5C2', 'VI.C5C3', 'VI.C5C4', 
                    'VI.C5C5', 'VI.C5C6', 'VI.C6A', 'VI.C6B1', 'VI.C6B2', 
                    'VI.C6B3', 'VI.C6C1', 'VI.C6C2', 'VI.C6C3', 'VI.C6C4', 
                    'VI.C6C5', 'VI.C6C6', 'VII.A', 'VII.B.1', 'VII.B.2', 
                    'VII.B.3', 'VII.C.1', 'VII.C.2', 'VII.C.3', 'VII.C.4', 
                    'VII.C.5', 'VII.C.6', 'VII.D.1', 'VII.D.2', 'VII.D.3', 
                    'VII.D.4', 'VII.D.5', 'VII.D.6', 'VII.E.1', 'VII.E.2', 
                    'VII.E.3', 'VII.E.4', 'VII.E.5', 'VII.E.6', 'VII.F.ddd', 
                    'VII.F.ddu', 'VII.F.ddb', 'VII.F.dud', 'VII.F.duu', 'VII.F.dub', 
                    'VII.F.dbd', 'VII.F.dbu', 'VII.F.dbb', 'VII.F.udd', 'VII.F.udu', 
                    'VII.F.udb', 'VII.F.uud', 'VII.F.uuu', 'VII.F.uub', 'VII.F.ubd', 
                    'VII.F.ubu', 'VII.F.ubb', 'VII.F.bdd', 'VII.F.bdu', 'VII.F.bdb', 
                    'VII.F.bud', 'VII.F.buu', 'VII.F.bub', 'VII.F.bbd', 'VII.F.bbu', 
                    'VII.F.bbb', 'VII.Ga.A', 'VII.Ga.B', 'VII.Ga.C', 'VII.Ga.D', 
                    'VII.Ga.E', 'VII.Ga.F', 'VII.Ga.G', 'VII.Gb.ddd', 'VII.Gb.ddu', 
                    'VII.Gb.dud', 'VII.Gb.duu', 'VII.Gb.udd', 'VII.Gb.udu', 'VII.Gb.uud', 
                    'VII.Gb.uuu', 'VII.Gc.1', 'VII.Gc.2', 'VII.Gc.3', 'VII.Gd.1', 
                    'VII.Gd.2', 'VII.Gd.3', 'VII.Ge.1', 'VII.Ge.2', 'VII.Ge.4', 
                    'VII.Gf.1', 'VII.Gf.2', 'VII.Gg', 'VIII.AA', 'VIII.AB1', 
                    'VIII.AB2', 'VIII.AB3', 'VIII.AC1', 'VIII.AC2', 'VIII.AC3', 
                    'VIII.AC4', 'VIII.AC5', 'VIII.AC6', 'VIII.B1A', 'VIII.B1B1', 
                    'VIII.B1B2', 'VIII.B1B3', 'VIII.B1C1', 'VIII.B1C2', 'VIII.B1C3', 
                    'VIII.B1C4', 'VIII.B1C5', 'VIII.B1C6', 'VIII.B2A', 'VIII.B2B1', 
                    'VIII.B2B2', 'VIII.B2B3', 'VIII.B2C1', 'VIII.B2C2', 'VIII.B2C3', 
                    'VIII.B2C4', 'VIII.B2C5', 'VIII.B2C6', 'VIII.B3A', 'VIII.B3B1', 
                    'VIII.B3B2', 'VIII.B3B3', 'VIII.B3C1', 'VIII.B3C2', 'VIII.B3C3', 
                    'VIII.B3C4', 'VIII.B3C5', 'VIII.B3C6', 'VIII.C1A', 'VIII.C1B1', 
                    'VIII.C1B2', 'VIII.C1B3', 'VIII.C1C1', 'VIII.C1C2', 'VIII.C1C3', 
                    'VIII.C1C4', 'VIII.C1C5', 'VIII.C1C6', 'VIII.C2A', 'VIII.C2B1', 
                    'VIII.C2B2', 'VIII.C2B3', 'VIII.C2C1', 'VIII.C2C2', 'VIII.C2C3', 
                    'VIII.C2C4', 'VIII.C2C5', 'VIII.C2C6', 'VIII.C3A', 'VIII.C3B1', 
                    'VIII.C3B2', 'VIII.C3B3', 'VIII.C3C1', 'VIII.C3C2', 'VIII.C3C3', 
                    'VIII.C3C4', 'VIII.C3C5', 'VIII.C3C6', 'VIII.C4A', 'VIII.C4B1', 
                    'VIII.C4B2', 'VIII.C4B3', 'VIII.C4C1', 'VIII.C4C2', 'VIII.C4C3', 
                    'VIII.C4C4', 'VIII.C4C5', 'VIII.C4C6', 'VIII.C5A', 'VIII.C5B1', 
                    'VIII.C5B2', 'VIII.C5B3', 'VIII.C5C1', 'VIII.C5C2', 'VIII.C5C3', 
                    'VIII.C5C4', 'VIII.C5C5', 'VIII.C5C6', 'VIII.C6A', 'VIII.C6B1', 
                    'VIII.C6B2', 'VIII.C6B3', 'VIII.C6C1', 'VIII.C6C2', 'VIII.C6C3', 
                    'VIII.C6C4', 'VIII.C6C5', 'VIII.C6C6', 'IX.A', 'IX.B.1', 
                    'IX.B.2', 'IX.B.3', 'IX.C.1', 'IX.C.2', 'IX.C.3', 
                    'IX.C.4', 'IX.C.5', 'IX.C.6', 'IX.D.1', 'IX.D.2', 
                    'IX.D.3', 'IX.D.4', 'IX.D.5', 'IX.D.6', 'IX.E.1', 
                    'IX.E.2', 'IX.E.3', 'IX.E.4', 'IX.E.5', 'IX.E.6', 
                    'IX.F.ddd', 'IX.F.ddu', 'IX.F.ddb', 'IX.F.dud', 'IX.F.duu', 
                    'IX.F.dub', 'IX.F.dbd', 'IX.F.dbu', 'IX.F.dbb', 'IX.F.udd', 
                    'IX.F.udu', 'IX.F.udb', 'IX.F.uud', 'IX.F.uuu', 'IX.F.uub', 
                    'IX.F.ubd', 'IX.F.ubu', 'IX.F.ubb', 'IX.F.bdd', 'IX.F.bdu', 
                    'IX.F.bdb', 'IX.F.bud', 'IX.F.buu', 'IX.F.bub', 'IX.F.bbd', 
                    'IX.F.bbu', 'IX.F.bbb', 'IX.Ga.A', 'IX.Ga.B', 'IX.Ga.C', 
                    'IX.Ga.D', 'IX.Ga.E', 'IX.Ga.F', 'IX.Ga.G', 'IX.Gb.ddd', 
                    'IX.Gb.ddu', 'IX.Gb.dud', 'IX.Gb.duu', 'IX.Gb.udd', 'IX.Gb.udu', 
                    'IX.Gb.uud', 'IX.Gb.uuu', 'IX.Gc.1', 'IX.Gc.2', 'IX.Gc.3', 
                    'IX.Gd.1', 'IX.Gd.2', 'IX.Gd.3', 'IX.Ge.1', 'IX.Ge.2', 
                    'IX.Ge.4', 'IX.Gf.1', 'IX.Gf.2', 'IX.Gg']
