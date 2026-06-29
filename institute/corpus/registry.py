"""Trial registry skeleton (CONSTITUTION §5/§11C). Every hypothesis logged, incl. failures.

A1 ships the append/list surface only; deflation maths arrives in A2.
"""
from institute.corpus import store


def log_trial(path, trial):
    store.append_jsonl(path, [trial.dict() if hasattr(trial, "dict") else trial])


def all_trials(path):
    return store.load_jsonl(path)


def trial_count(path):
    """True search intensity — what overfitting corrections must deflate against."""
    return len(all_trials(path))
