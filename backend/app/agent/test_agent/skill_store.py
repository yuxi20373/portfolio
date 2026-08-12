"""Postgres-backed skill storage for test_agent - lets skill content (and
even brand-new fab/function identities) be created/edited through the
"Skill Manage" admin page (see routers/test_agent_skills.py) and take
effect immediately, without touching local files or redeploying.

Reuses the same Postgres store process_agent already opened (_shared_store,
one connection pool for the whole app), just a distinct top-level namespace
prefix ("test_agent_skills") so it never collides with process_agent's own
memories or test_agent's chat-session store usage ("test_agent", <session>).

Namespace layout: ("test_agent_skills", fab, role) where role is either
"_shared" (fab-wide) or a function name - one namespace per (fab, role),
holding one key per skill file: "{skill_name}/SKILL.md" -> {"content":
str, "encoding": "utf-8"}. This is exactly the layout deepagents'
StoreBackend expects (see tools.py's shared_backend), so skills read
through it need no translation.
"""

from pathlib import Path

# Imported straight from process_agent (not via .tools) to avoid a circular
# import - tools.py itself imports skill_store (inside _discover_identities,
# lazily) to stay DB-driven, so skill_store can't import tools.py at module
# level; both modules get _shared_store from the same original source.
from ..process_agent.tools import _shared_store

_SKILLS_ROOT = Path(__file__).resolve().parent.parent / "process_agent" / "skills"
_NS_PREFIX = "test_agent_skills"


def _namespace(fab: str, role: str) -> tuple:
    return (_NS_PREFIX, fab, role)


def _key(skill_name: str) -> str:
    # Leading slash matters: CompositeBackend forwards paths to the routed
    # backend with the matched route prefix stripped but the leading slash
    # kept (e.g. "/L8A/Cell/generate-report/SKILL.md" through route
    # "/L8A/Cell/" arrives here as "/generate-report/SKILL.md") - the store
    # key must match that exactly, unlike FilesystemBackend where paths are
    # real virtual-root-relative filesystem paths and this was implicit.
    return f"/{skill_name}/SKILL.md"


def list_identities() -> dict[str, list[str]]:
    """fab -> sorted list of function names (excluding "_shared"), read
    live from the store's namespace hierarchy - a brand-new fab or
    function becomes visible the moment its first skill file is saved,
    no code change or restart needed."""
    namespaces = _shared_store.list_namespaces(prefix=(_NS_PREFIX,), max_depth=3)
    identities: dict[str, list[str]] = {}
    for ns in namespaces:
        if len(ns) != 3:
            continue
        _, fab, role = ns
        identities.setdefault(fab, [])
        if role != "_shared":
            identities[fab].append(role)
    for fab in identities:
        identities[fab].sort()
    return identities


def list_skill_files() -> list[dict]:
    """Every skill file currently in the store, across all fab/role
    namespaces - what the Skill Manage page's list view shows."""
    namespaces = _shared_store.list_namespaces(prefix=(_NS_PREFIX,), max_depth=3)
    files = []
    for ns in namespaces:
        if len(ns) != 3:
            continue
        _, fab, role = ns
        for item in _shared_store.search(ns):
            # key is "/{skill_name}/SKILL.md" (see _key) - strip the
            # leading slash before splitting so skill_name doesn't end up
            # with one baked in.
            parts = item.key.strip("/").split("/")
            skill_name = parts[0] if parts else item.key
            files.append(
                {
                    "fab": fab,
                    "role": role,
                    "skill_name": skill_name,
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                }
            )
    files.sort(key=lambda f: (f["fab"], f["role"], f["skill_name"]))
    return files


def get_skill_content(fab: str, role: str, skill_name: str) -> str | None:
    item = _shared_store.get(_namespace(fab, role), _key(skill_name))
    return item.value.get("content") if item else None


def save_skill_content(fab: str, role: str, skill_name: str, content: str) -> None:
    """Create-or-update - the same call handles both, matching how the
    Skill Manage page's editor works (open an existing skill or start a
    brand-new one, then Save)."""
    _shared_store.put(_namespace(fab, role), _key(skill_name), {"content": content, "encoding": "utf-8"})


def delete_skill_file(fab: str, role: str, skill_name: str) -> None:
    _shared_store.delete(_namespace(fab, role), _key(skill_name))


def seed_from_disk() -> list[str]:
    """One-time migration: copy every {FAB}/{role}/{skill}/SKILL.md
    currently on disk into the store, skipping any (fab, role, skill)
    already present there. Safe to call more than once. Returns the list
    of "fab/role/skill" paths actually seeded."""
    if not _SKILLS_ROOT.exists():
        return []
    seeded = []
    for fab_dir in sorted(p for p in _SKILLS_ROOT.iterdir() if p.is_dir() and p.name != "_shared"):
        for role_dir in sorted(p for p in fab_dir.iterdir() if p.is_dir()):
            role = role_dir.name
            for skill_dir in sorted(p for p in role_dir.iterdir() if p.is_dir()):
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue
                skill_name = skill_dir.name
                if get_skill_content(fab_dir.name, role, skill_name) is not None:
                    continue
                save_skill_content(fab_dir.name, role, skill_name, skill_md.read_text(encoding="utf-8"))
                seeded.append(f"{fab_dir.name}/{role}/{skill_name}")
    return seeded
