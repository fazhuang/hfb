def validate_scan(result):
    errors = []
    if not result.root_exists:
        errors.append("docs/ directory not found.")
    if result.mdmd_files:
        errors.append(f"Found .md.md files: {len(result.mdmd_files)}")
    if result.duplicate_document_ids:
        errors.append(
            f"Found duplicate document_id groups: {len(result.duplicate_document_ids)}"
        )
    if result.known_duplicate_candidates:
        errors.append(
            f"Found known legacy duplicate files: {len(result.known_duplicate_candidates)}"
        )
    return len(errors) == 0, errors
