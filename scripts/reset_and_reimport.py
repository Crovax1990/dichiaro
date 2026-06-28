"""
Reset the SQLite database and reimport all PDF tax declarations from scratch.

Usage (local):
    cd dichiarazione730-analyzer
    uv run python scripts/reset_and_reimport.py

Usage (Docker):
    docker compose up -d
    docker compose exec app uv run python scripts/reset_and_reimport.py

This deletes the database, recreates the schema, then scans
data/*.pdf for all years and reimports everything.
"""

import re
import sys
from pathlib import Path

# Ensure project root is in PYTHONPATH
_HERE = Path(__file__).resolve().parent
_PROJECT = _HERE.parent
sys.path.insert(0, str(_PROJECT))

from sqlalchemy.orm import Session

from backend.models import Base, Persona, create_engine_session
from backend.parser.importer import import_pdf_to_db


RE_FILENAME = re.compile(r"DichiarazioneTestuale(\d{4})_([A-Z0-9]{16})_")


def _find_pdfs(data_dir: Path) -> list[tuple[int, str, Path]]:
    pdfs = sorted(data_dir.glob("DichiarazioneTestuale*.pdf"))
    results = []
    for pdf in pdfs:
        m = RE_FILENAME.search(pdf.name)
        if not m:
            print(f"  ⚠ Skipping {pdf.name}: unable to extract year/CF from filename")
            continue
        anno = int(m.group(1))
        cf = m.group(2)
        results.append((anno, cf, pdf))
    return results


def _get_or_create_persona(cf: str, session: Session) -> Persona:
    existing = session.query(Persona).filter_by(codice_fiscale=cf).first()
    if existing:
        return existing
    p = Persona(codice_fiscale=cf, nome="", cognome="")
    session.add(p)
    session.flush()
    return p


def main():
    db_path = _PROJECT / "backend" / "analyzer.db"
    engine, SessionLocal = create_engine_session(str(db_path))
    data_dir = _PROJECT / "data"

    if not data_dir.exists():
        print(f"ERROR: data/ directory not found at {data_dir}")
        sys.exit(1)

    pdfs = _find_pdfs(data_dir)
    if not pdfs:
        print(f"ERROR: no matching PDF files found in {data_dir}")
        sys.exit(1)

    # Drop and recreate
    print(f"Resetting database: {db_path}")
    if db_path.exists():
        db_path.unlink()

    engine, SessionLocal = create_engine_session(str(db_path))
    Base.metadata.create_all(engine)
    session = SessionLocal()

    total = len(pdfs)
    ok = 0
    errors: list[tuple[str, str]] = []
    for anno, cf, pdf in pdfs:
        progress = f"[{ok + len(errors) + 1}/{total}]"
        print(f"  {progress} {anno} — {cf} — {pdf.name}")
        try:
            persona = _get_or_create_persona(cf, session)
            import_pdf_to_db(str(pdf), persona.id, anno, session)
            ok += 1
        except Exception as e:
            msg = str(e)
            print(f"    ERROR: {msg}", file=sys.stderr)
            errors.append((pdf.name, msg))
            session.rollback()

    session.close()
    print(f"\nDone! {ok}/{total} PDFs imported successfully.")
    if errors:
        print(f"{len(errors)} errors:", file=sys.stderr)
        for name, msg in errors:
            print(f"  {name}: {msg}", file=sys.stderr)
    print(f"Database: {db_path}")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
