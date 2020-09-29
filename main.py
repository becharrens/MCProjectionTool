from dfa.dfa import DFA
from parser import parser


def main():
    try:
        protocols = parser.parse_file("examples/examples.scr")
        for proto_name, protocol in protocols.items():
            role = None
            try:
                print(f"PROTOCOL {proto_name}\n")
                print(str(protocol.gtype))
                projections = protocol.gtype.project(set(protocol.roles))
                print("Preliminary projections")
                for role, ltype in projections.items():
                    print(f"{role}@{protocol.protocol}:\n")
                    print(str(ltype), "\n\n")

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
                print(f"Error: {name}:", e)
                print("!!!!!!!!!!!!!!!!!!!!!!!!")
                print("\n=============================>\n")

    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()
