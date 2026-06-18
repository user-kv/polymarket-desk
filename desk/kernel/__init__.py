"""
desk.kernel — the IMMUTABLE protected core.

Nothing in the self-modification loop (desk/tools/*, autopsy-proposed changes) is
ever permitted to edit files in this package. The overseer (desk/overseer.py) and
the promotion gate verify the kernel's hash before any self-written tool goes live.

If you (the human) ever change a rule here, do it deliberately and re-baseline the
hash with:  python -m desk.kernel.invariants --rebaseline
"""
