from enum import Enum

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
        self, proj_role: str, participant: str, action_type: ActionType, payload: str
    ):
        self.participant = participant
        self.payload = payload
        self.action_type = action_type
        self.proj_role = proj_role

    def get_participant(self) -> str:
        return self.participant

    def dual(self):
        return LAction(
            self.participant, self.proj_role, self.action_type.dual(), self.payload
        )

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, LAction):
            return False
        return self.__hash__() == o.__hash__()

    def __hash__(self) -> int:
        return str(self).__hash__() % HASH_SIZE

    def __str__(self) -> str:
        return f"{self.participant}{self.action_type}{self.payload}"
