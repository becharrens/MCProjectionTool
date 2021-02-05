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


class Protocol:
    def __init__(self, protocol: str, roles: List[str], gtype: GType) -> None:
        self.protocol = protocol
        self.roles = roles
        self.gtype: GType = gtype.normalise()
        self.gtype.ensure_unique_tvars({}, set(), 0)

    def __str__(self) -> str:
        tab = "\t"
        return f"global protocol {self.protocol}({', '.join(self.roles)}) {{\n{self.gtype.to_string(tab)}\n}}"

    def __repr__(self) -> str:
        return self.__str__()


def parse_file(file_name: str, parser_name: str) -> Dict[str, Protocol]:
    if parser_name == "scribble":
        parser = Lark.open("scribble-syntax.lark", rel_to=__file__, parser="lalr")
        transformer = ScribbleToGType()
    elif parser_name == "mpst":
        parser = Lark.open("mc_mpst_syntax.lark", rel_to=__file__, parser="lalr")
        transformer = MPSTToGType()
    else:
        assert False, f"Invalid parser name provided: {parser_name}"
    # parser = Lark.open("syntax.lark", rel_to=__file__, parser="lalr")

    with open(file_name, "r") as f:
        protocols = f.read()

    tree = parser.parse(protocols)
    # transformer = ScribbleToGType()
    # transformer = TreeToGType()
    return transformer.transform(tree)


class MPSTToGType(Transformer):
    # def start(self, decls):
    #     return {dec}
    def END(self, tok):
        return GEnd()

    def tvar(self, tvar):
        return GRecVar(tvar[0])

    def recursion(self, values):
        tvar, gtype = values
        return GRecursion(tvar, gtype)

    # def message_transfer(self, values):
    def message_transfer(self, args):
        sender, recv, payload, cont = args
        label, payload_fields = payload
        payload_fields = payload_fields or []
        action = GAction([sender, recv], label, payload_fields)
        return GMessagePass(action, cont)

    def payload(self, args):
        if len(args) == 1:
            payload_type = args[0]
            return None, payload_type
        payload_name, payload_type = args
        return payload_name, payload_type

    def payload_decl(self, payload_fields):
        return payload_fields

    def labelled_message(self, args):
        if len(args) == 1:
            label = args[0]
            return label, None
        else:
            label, payloads = args
            return label, payloads

    def mchoice(self, values):
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


class ScribbleToGType(Transformer):
    def tvar(self, tvar):
        return GRecVar(tvar[0])

    def recursion(self, values):
        tvar, gtype = values
        return GRecursion(tvar, gtype)

    # def message_transfer(self, values):
    def message_transfer(self, args):
        if len(args) == 3:
            payload, sender, recv = args
            cont = GEnd()
        elif len(args) == 4:
            payload, sender, recv, cont = args
        else:
            assert False, f"Invalid message_transfer args: {args}"
        label, payload_fields = payload
        payload_fields = payload_fields or []
        action = GAction([sender, recv], label, payload_fields)
        return GMessagePass(action, cont)

    def payload(self, args):
        if len(args) == 1:
            payload_type = args[0]
            return None, payload_type
        payload_name, payload_type = args
        return payload_name, payload_type

    def payload_decl(self, payload_fields):
        return payload_fields

    def labelled_message(self, args):
        if len(args) == 1:
            label = args[0]
            return label, None
        else:
            label, payloads = args
            return label, payloads

    def mchoice(self, values):
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
    OR = str
    REC = str
    MCHOICE = str
    FROM = str
    TO = str
    MAP = str
