import argparse
from . import __version__
from . import docs

def main(argv=None):
    parser = argparse.ArgumentParser(prog="hgt", description="HFB Governance Toolkit")
    parser.add_argument("--version", action="version", version=f"HGT {__version__}")
    sub = parser.add_subparsers(dest="module")

    docs_parser = sub.add_parser("docs", help="Docs governance commands")
    docs_sub = docs_parser.add_subparsers(dest="command")
    for name in ["inventory", "scaffold", "validate", "report", "all"]:
        docs_sub.add_parser(name)

    args = parser.parse_args(argv)

    if args.module == "docs":
        if args.command == "inventory":
            return docs.inventory(args)
        if args.command == "scaffold":
            return docs.scaffold(args)
        if args.command == "validate":
            return docs.validate(args)
        if args.command == "report":
            return docs.report(args)
        if args.command == "all":
            return docs.all_cmd(args)

    parser.print_help()
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
