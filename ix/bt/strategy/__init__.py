

from .base import Strategy
from .new import *




def all_strategies() -> list[type[Strategy]]:

    return [
        UsIsmPmiManuEB,
        UsOecdLeiEB,
        SectorRotationCESI,
        SectorRotationMom90,
    ]
