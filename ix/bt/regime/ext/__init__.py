from .UsIsmPmiManu import UsIsmPmiManu
from .UsOecdLeading import UsOecdLeading
from .UstY10BE import UstY10BE
from .UsExpRealRate12M import UsExpRealRate12M, UsExpInflation10Y
from typing import Type
from ..base import Regime


def all_regimes() -> list[Type[Regime]]:

    return [
        UsIsmPmiManu,
        UsOecdLeading,
        UstY10BE,
        UsExpInflation10Y,
        UsExpRealRate12M,
    ]
