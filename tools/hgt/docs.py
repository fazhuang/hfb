from .scanner import scan_docs
from .reporter import write_audit_report, append_report
from .upgrader import scaffold_docs
from .validator import validate_scan

def inventory(args):
    result = scan_docs()
    out = write_audit_report(result)
    print(f"✔ inventory complete: {out}")
    print(f"Markdown: {len(result.markdown_files)} | md.md: {len(result.mdmd_files)} | missing header: {len(result.missing_yaml_header)}")
    return 0

def scaffold(args):
    actions = scaffold_docs()
    append_report("upgrade", "Docs Upgrade Report", actions)
    append_report("changelog", "Docs Changelog", actions)
    result = scan_docs()
    write_audit_report(result)
    print("✔ scaffold complete")
    for action in actions:
        print(f"- {action}")
    return 0

def validate(args):
    result = scan_docs()
    write_audit_report(result)
    ok, errors = validate_scan(result)
    if ok:
        print("✔ validate passed")
        return 0
    print("✖ validate failed")
    for error in errors:
        print(f"- {error}")
    return 1

def report(args):
    result = scan_docs()
    out = write_audit_report(result)
    print(f"✔ report generated: {out}")
    return 0

def all_cmd(args):
    inventory(args)
    scaffold(args)
    return validate(args)
