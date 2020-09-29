from abc import ABC, abstractmethod
from typing import Dict, Set

from gtypes.gaction import GAction
from ltypes.ltype import LType


class GType(ABC):
    @abstractmethod
    def project(self, roles: Set[str]) -> Dict[str, LType]:
        pass

    @abstractmethod
    def first_actions(self, tvars: Set[str]) -> Set[GAction]:
        pass

    @abstractmethod
    def set_rec_gtype(self, tvar: str, gtype) -> None:
        pass

    @abstractmethod
    def hash(self, tvars: Set[str]) -> int:
        pass

    @abstractmethod
    def to_string(self, indent: str) -> str:
        pass

    @abstractmethod
    def normalise(self):
        pass

    @abstractmethod
    def has_rec_var(self, tvar: str) -> bool:
        pass
