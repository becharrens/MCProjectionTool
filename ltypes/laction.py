from enum import Enum
from typing import List, Tuple

from ltypes import HASH_SIZE


class ActionType(Enum):
    send = 0
    recv = 1

    def dual(self):
        return ActionType(1 - self.value)

    def __str__(self):
        if self.value == 0:
            return "!"
        return "?"


class LAction:
    def __init__(
        self,
        proj_role: str,
        participant: str,
        action_type: ActionType,
        label: str,
        payloads: List[Tuple[str, str]],
    ):
        self.participant = participant
        self.label = label
        self.action_type = action_type
        self.proj_role = proj_role
        self.payloads = payloads

    def get_participant(self) -> str:
        return self.participant

    def get_payloads(self):
        return self.payloads

    def get_label(self):
        return self.label

    def dual(self):
        return LAction(
            self.participant,
            self.proj_role,
            self.action_type.dual(),
            self.label,
            self.payloads,
        )

    def hash(self):
        return str(self).__hash__() % HASH_SIZE

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, LAction):
            return False
        return self.__str__() == o.__str__()

    def __hash__(self) -> int:
        return self.hash()

    def __str__(self) -> str:
        return f"{self.participant}{self.action_type}{self.label}"
