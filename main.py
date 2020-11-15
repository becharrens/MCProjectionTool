from dfa.dfa import DFA
from parser import parser as scr_parser
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Tool to project Scribble protocols with mixed choice"
    )
    parser.add_argument(
        "file",
        metavar="file",
        type=str,
        help="path to the file where the scribble protocols are defined",
    )
    args = parser.parse_args()
    try:
        protocols = scr_parser.parse_file(args.file)
        for proto_name, protocol in protocols.items():
            role = None
            try:
                print(f"PROTOCOL {proto_name}\n")
                print(str(protocol.gtype))
                projections = protocol.gtype.project(set(protocol.roles))
                print("Preliminary projections")
                projections = {
                    role: ltype.normalise() for role, ltype in projections.items()
                }
                # p = {}
                # for role in protocol.roles:
                #     p[role] = projections[role].normalise()
                # projections = p
                for role, ltype in projections.items():
                    print(f"{role}@{protocol.protocol}:\n")
                    print(str(ltype), "\n\n")

                print("Checking projections...\n\n")
                for ltype in projections.values():
                    ltype.check_valid_projection()
                print("Normalised projections")
                for role, ltype in projections.items():
                    dfa = DFA(ltype)
                    new_ltype = dfa.translate()
                    print(f"{role}@{protocol.protocol}:\n")
                    print(str(new_ltype), "\n\n")
                print("\n\n=============================>\n")
            except Exception as e:
                name = "@".join([x for x in [role, proto_name] if x is not None])
                print("!!!!!!!!!!!!!!!!!!!!!!!!")
                print(f"Error: {name}:", repr(e))
                print("!!!!!!!!!!!!!!!!!!!!!!!!")
                print("\n=============================>\n")

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()
