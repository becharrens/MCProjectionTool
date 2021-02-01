from typing import Dict


class NameGen:
    def __init__(self) -> None:
        super().__init__()
        self.names: Dict[str, int] = {}

    def unique_name(self, name: str) -> str:
        if name not in self.names:
            self.names[name] = 2
            return name

        uid = self.names[name]
        new_name = NameGen.gen_name(name, uid)
        while new_name in self.names:
            uid += 1
            new_name = NameGen.gen_name(name, uid)

        self.names[name] = uid + 1
        self.names[new_name] = 2
        return new_name

    @staticmethod
    def gen_name(name: str, uid: int) -> str:
        return f"{name}_{uid}"
