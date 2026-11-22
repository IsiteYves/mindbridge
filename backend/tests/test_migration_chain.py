"""Static checks on migrations/versions/*.py. These parse the files as text
and need no database at all
"""

import re
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations" / "versions"

REVISION_RE = re.compile(r"""^revision\s*=\s*['"]([^'"]+)['"]""", re.M)
DOWN_REVISION_RE = re.compile(r"""^down_revision\s*=\s*(None|['"]([^'"]+)['"])""", re.M)


def _load_chain():
    """Return {revision: (down_revision_or_None, filename)} for every migration."""
    revisions = {}
    for path in MIGRATIONS_DIR.glob("*.py"):
        text = path.read_text()
        revision_match = REVISION_RE.search(text)
        down_match = DOWN_REVISION_RE.search(text)
        assert revision_match, f"{path.name} has no `revision = ...` line"
        assert down_match, f"{path.name} has no `down_revision = ...` line"
        down_value = None if down_match.group(1) == "None" else down_match.group(2)
        revisions[revision_match.group(1)] = (down_value, path.name)
    return revisions


def test_every_migration_has_a_unique_revision_id():
    files_by_revision = {}
    for path in MIGRATIONS_DIR.glob("*.py"):
        revision = REVISION_RE.search(path.read_text()).group(1)
        assert revision not in files_by_revision, (
            f"{path.name} and {files_by_revision[revision]} both declare revision {revision!r}"
        )
        files_by_revision[revision] = path.name


def test_there_is_exactly_one_root_migration():
    revisions = _load_chain()
    roots = [name for down, name in revisions.values() if down is None]
    assert len(roots) == 1, f"expected exactly one migration with down_revision = None, found: {roots}"


def test_no_down_revision_is_shared_by_two_migrations():
    """A shared down_revision is a branch: two migrations both claiming to
    follow the same one. This is precisely the bug this file exists to catch
    — see the module docstring. Alembic would refuse to run such a history
    with a "multiple heads" error.
    """
    revisions = _load_chain()
    seen = {}
    for down, name in revisions.values():
        if down is None:
            continue
        if down in seen:
            raise AssertionError(
                f"{name!r} and {seen[down]!r} both declare down_revision = {down!r}. "
                "Alembic cannot run a branched history; one of these needs to be rebased."
            )
        seen[down] = name


def test_every_down_revision_points_at_a_migration_that_actually_exists():
    revisions = _load_chain()
    known = set(revisions.keys())
    for down, name in revisions.values():
        if down is not None:
            assert down in known, f"{name} declares down_revision = {down!r}, which no migration file defines"


def test_the_chain_is_one_unbroken_line_from_root_to_tip():
    """Walks the chain from the root migration forward. If every earlier
    check passes (one root, no shared down_revision, every down_revision
    resolves), this walk necessarily reaches every migration exactly once —
    this test exists mainly to make that conclusion explicit and to report
    exactly how many migrations were reached if it ever does not.
    """
    revisions = _load_chain()
    current = next(rev for rev, (down, _) in revisions.items() if down is None)
    chain = [revisions[current][1]]
    children_of = {}
    for rev, (down, _) in revisions.items():
        if down is not None:
            children_of.setdefault(down, []).append(rev)

    while current in children_of:
        children = children_of[current]
        assert len(children) == 1, f"{current} has multiple children: {children}"
        current = children[0]
        chain.append(revisions[current][1])

    assert len(chain) == len(revisions), (
        f"only reached {len(chain)} of {len(revisions)} migrations by walking from the root; "
        f"the rest are unreachable: {sorted(set(n for _, n in revisions.values()) - set(chain))}"
    )
