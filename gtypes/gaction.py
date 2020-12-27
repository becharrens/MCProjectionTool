import string
from typing import List, Optional, Tuple

from gtypes import HASH_SIZE
from ltypes.laction import LAction, ActionType


class GAction:
    def __init__(
        self,
        participants: List[str],
        label: str,
        payloads: List[Tuple[Optional[str], str]],
    ):
        assert len(set(participants)) == 2
        self.participants = participants
        self.label = label
        self.payloads = payloads

    def get_participants(self):
        return self.participants

    def project(self, role):
        if role == self.participants[0]:
            return LAction(
                self.participants[0],
                self.participants[1],
                ActionType.send,
                self.label,
                self.payloads,
            )
        if role == self.participants[1]:
            return LAction(
                self.participants[1],
                self.participants[0],
                ActionType.recv,
                self.label,
                self.payloads,
            )
        return None

    def get_payloads(self):
        return self.payloads

    def get_label(self):
        return self.label

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, GAction):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return str(self).__hash__() % HASH_SIZE

    def __str__(self) -> str:
        return f'{"->".join(self.participants)}:{self.label}'
