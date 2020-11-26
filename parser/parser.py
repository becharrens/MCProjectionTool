from collections import OrderedDict
from typing import Dict, List

from lark import Lark, Transformer

from gtypes.gaction import GAction
from gtypes.gmchoice import GChoice
from gtypes.gend import GEnd
from gtypes.gmessage_pass import GMessagePass
from gtypes.grec_var import GRecVar
from gtypes.grecursion import GRecursion
from gtypes.gtype import GType


def set_gtype_participants(gtype: GType):
    tvar0 = "$tvar"
    tvar_participants = OrderedDict({tvar0: (set(), set())})
    gtype.all_participants(tvar0, tvar_participants)
    ppt_mapping = {}

    final_tvars = set()
    for curr_tvar, (curr_ppts, curr_tvars) in tvar_participants.items():
        tvars_to_explore = set(curr_tvars)
        explored_tvars = {curr_tvar}
        while len(tvars_to_explore) > 0:
            tvar = tvars_to_explore.pop()
            if tvar not in explored_tvars:
                # If tvar hasn't been seen before add it to seen set
                ppts, tvars = tvar_participants[tvar]
                curr_ppts |= ppts
                explored_tvars.add(tvar)
                if tvar not in final_tvars:
                    # If final participant set hasn't been computed, explore
                    # tvar recursively
                    tvars_to_explore |= tvars

        ppt_mapping[curr_tvar] = curr_ppts
        final_tvars.add(curr_tvar)
    gtype.set_rec_participants(ppt_mapping)


class Protocol:
    def __init__(self, protocol: str, roles: List[str], gtype: GType) -> None:
        self.protocol = protocol
        self.roles = roles
        set_gtype_participants(gtype)
        self.gtype: GType = gtype.normalise()
        self.gtype.ensure_unique_tvars({}, set(), 0)

    def __str__(self) -> str:
        tab = "\t"
        return f"global protocol {self.protocol}({', '.join(self.roles)}) {{\n{self.gtype.to_string(tab)}\n}}"

    def __repr__(self) -> str:
        return self.__str__()


def parse_file(file_name) -> Dict[str, Protocol]:
    parser = Lark.open("syntax.lark", rel_to=__file__, parser="lalr")

    with open(file_name, "r") as f:
        protocols = f.read()

    tree = parser.parse(protocols)
    transformer = TreeToGType()
    return transformer.transform(tree)


class TreeToGType(Transformer):
    # def start(self, decls):
    #     return {dec}
    def END(self, tok):
        return GEnd()

    def tvar(self, tvar):
        return GRecVar(tvar[0])

    def recursion(self, values):
        tvar, gtype = values
        return GRecursion(tvar, gtype)

    def message_transfer(self, values):
        sender, recv, payload, cont = values
        action = GAction([sender, recv], payload)
        return GMessagePass(action, cont)

    def choice(self, values):
        return GChoice(values)

    def decl(self, values):
        name, roles, gtype = values
        return Protocol(name, roles, gtype)

    def start(self, declartions):
        return {decl.protocol: decl for decl in declartions}

    def interaction(self, values):
        return values[0]

    CNAME = str
    WORD = str
    role_decl = list
