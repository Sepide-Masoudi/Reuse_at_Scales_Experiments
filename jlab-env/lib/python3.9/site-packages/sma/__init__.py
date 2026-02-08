"""
Social-Ecological-System Motif Analyser (SMA).

The module provides the following main functions:
    - reading SES from CSV files
    - analysing SES', especially counting 3- and 4-motifs with or without
      taking nodal attributes into account
    - generating random SES'
    - exchanging information with R (using statnet on the R side)

"""

# load core module first
from .properties import *
from .helper import *
from .io import *
from .classify import *
from .classify_dimotifs import *
from .iterate import *
from .analyse import *
from .generate import *

# load high level modules
from .analyse_linalg import *
from .analyse_frontend import *
from .analyse_triangles import *
from .analyse_cooccurrence import *
from .analyse_distribution import *
from .analyse_simulate import *
from .draw import *
from .rbridge import *

# create info database
from .motif_info import *