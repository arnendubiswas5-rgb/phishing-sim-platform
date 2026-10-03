import csv
import io

from pydantic import EmailStr, TypeAdapter, ValidationError

_email_adapter = TypeAdapter(EmailStr)


def parse_target_csv(content: bytes) -> tuple[list[dict], int]:
    """Parses a target CSV (columns: email, first_name, last_name, department,
    position) into row dicts ready for Target(**row, group_id=...), plus a
    count of rows dropped for missing/malformed email.

    Rows are de-duplicated by lowercased email within the file itself (last
    occurrence wins) - duplicates against targets already in the database are
    handled separately by the caller via ON CONFLICT DO NOTHING.
    """
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        return [], 0

    # .lstrip("﻿") guards against a stray BOM character surviving into the
    # first header name even when the file wasn't decoded with utf-8-sig
    # upstream (e.g. it was re-saved through another tool first).
    normalized_fields = {name: name.strip().lstrip("﻿").lower() for name in reader.fieldnames}

    deduped: dict[str, dict] = {}
    skipped_invalid = 0

    for raw_row in reader:
        row = {
            normalized_fields.get(key, key): (value.strip() if isinstance(value, str) else value)
            for key, value in raw_row.items()
            if key is not None
        }

        try:
            email = str(_email_adapter.validate_python(row.get("email", ""))).lower()
        except ValidationError:
            skipped_invalid += 1
            continue

        deduped[email] = {
            "email": email,
            "first_name": row.get("first_name") or None,
            "last_name": row.get("last_name") or None,
            "department": row.get("department") or None,
            "position": row.get("position") or None,
        }

    return list(deduped.values()), skipped_invalid
