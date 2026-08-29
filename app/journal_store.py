import json
from pathlib import Path

JOURNAL_STORE = Path("data/journal.json")


def load_journals():
    if not JOURNAL_STORE.exists():
        return []

    with open(JOURNAL_STORE, "r", encoding="utf-8") as file:
        return json.load(file)

def save_journals(journals):
    with open(JOURNAL_STORE, "w", encoding="utf-8") as file:
        json.dump(
            journals,
            file,
            indent=2
        )

def add_journal(journal):
    journals = load_journals()

    journals.append(journal)

    save_journals(journals)

def delete_journal_record(
        document_id: str,
        session_id: str
    ):

    journals = load_journals()

    journals = [
        journal
        for journal in journals
        if not (
            journal.get("document_id") == document_id
            and journal.get("session_id") == session_id
        )
    ]

    save_journals(journals)

def get_journals_by_session(session_id: str):
    journals = load_journals()

    return [
        journal
        for journal in journals
        if journal.get("session_id") == session_id
    ]

def get_journal_by_session(
        document_id: str,
        session_id: str
    ):

    journals = get_journals_by_session(
        session_id
    )

    return next(
        (
            journal
            for journal in journals
            if journal.get("document_id") == document_id
        ),
        None
    )
