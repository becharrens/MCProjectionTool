from abc import ABC, abstractmethod
from typing import Set, Dict, Tuple, Any, Optional, List

from ltypes.laction import LAction


class LType(ABC):
    @abstractmethod
    def next_states(self) -> Dict[LAction, Set[Any]]:
        pass

    @abstractmethod
    def next_states_rec(self, tvars: Set[str]) -> Dict[LAction, Set[Any]]:
        pass

    @abstractmethod
    def first_actions(self) -> Set[LAction]:
        pass

    @abstractmethod
    def first_actions_rec(self, tvars: Set[str]) -> Set[LAction]:
        pass

    @abstractmethod
    def set_rec_ltype(self, tvar: str, ltype):
        pass

    @abstractmethod
    def hash(self) -> int:
        pass

    @abstractmethod
    def hash_rec(self, const_tvar_hash: bool) -> int:
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

    @abstractmethod
    def rename_tvars(self, tvars: Set[str], new_tvar, ltype):
        pass

    @abstractmethod
    def flatten_recursion(self):
        """Collapses consecutive recursive variables into a single one"""
        pass

    @abstractmethod
    def get_next_state(self, laction: LAction, tvars: Set[str]) -> Optional[Any]:
        pass

    @abstractmethod
    def check_valid_projection(self) -> None:
        pass

    @abstractmethod
    def calc_fst_actions_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        fst_actions: Dict[str, Set[LAction]],
        update_tvars: Dict[str, bool],
    ):
        pass

    @abstractmethod
    def set_fst_actions_rec(self, fst_actions: Dict[str, Set[LAction]]):
        pass

    @abstractmethod
    def calc_next_states_rec(
        self,
        tvar_deps: Dict[str, Set[str]],
        next_states: Dict[str, Dict[LAction, Set[Any]]],
        update_tvars: Dict[str, bool],
    ):
        pass

    @abstractmethod
    def set_next_states_rec(self, next_states: Dict[str, Dict[LAction, Set[Any]]]):
        pass

    @abstractmethod
    def max_rec_depth(self, curr_rec_depth: int) -> int:
        pass

    # @abstractmethod
    # def first_actions(self, tvars: Set[str]) -> None:
    #     pass
