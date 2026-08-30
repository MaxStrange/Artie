"""
Workspace resolution for Artie Tool.

Artie's components are moving out of this monorepo into separate repositories - ArDK,
ArtieCLI, ArtieWorkbench, ArtieDaemons, Artie00 - so Artie Tool can no longer assume that
everything it builds lives underneath its own checkout. This module owns the one thing
that assumption was built on: the mapping from a component name to the directory holding
that component's source.

Configuration is resolved in this order, highest priority first:

    1. command line arguments  (--workspace, --repo <name>=<path>, --channel)
    2. environment variables   (ARTIE_WORKSPACE, ARTIE_REPO_<NAME>, ARTIE_CHANNEL)
    3. a config file           (~/.artie/config.yaml, or $ARTIE_CONFIG)
    4. built-in defaults       (this monorepo's subdirectories)

The built-in defaults deliberately point at this repository's own subdirectories, so that
everything keeps working while the components are still here. As each component moves to
its own repository, its default changes to a clone under the workspace directory, and a
developer can always point `path` at a checkout of their own.

A repo configured with an explicit `path` is a development override: `workspace sync`
will never clone over it, fetch it, or otherwise touch it.

This module must not import `common`, which imports it.
"""
from typing import Dict, List, Optional
import dataclasses
import logging
import os
import pathlib
import subprocess

import yaml

LOGGER = logging.getLogger("artietool")

# Where a config file is looked for when $ARTIE_CONFIG is not set. Matches the convention
# already used by artie_tooling.artie_profile, which stores things under ~/.artie.
DEFAULT_CONFIG_PATH = pathlib.Path.home() / ".artie" / "config.yaml"

# Where repositories are cloned when they have no explicit `path`.
DEFAULT_WORKSPACE = pathlib.Path.home() / "artie-workspace"

GITHUB_ORG = "https://github.com/MaxStrange"


@dataclasses.dataclass
class RepoSpec:
    """
    Where one Artie component's source lives.
    """
    name: str
    # Clone URL, used when the repo has no local checkout yet.
    url: Optional[str] = None
    # Branch or tag to check out.
    ref: str = "main"
    # An explicit local checkout. When set, this is a development override: Artie Tool
    # reads from it and never clones, pulls, or writes over it.
    path: Optional[str] = None
    # Path relative to this monorepo's root, used while the component still lives here.
    # Ignored once `url`/`path` resolution takes over.
    monorepo_subdir: Optional[str] = None

    @property
    def is_dev_override(self) -> bool:
        return self.path is not None


# The components Artie Tool knows how to locate. While the split is in progress the
# monorepo_subdir entries are what actually get used; url/ref take over per component as
# each one moves out. Keep the names lowercase and hyphen-free so they are easy to spell
# in ${REPO:<name>} and in ARTIE_REPO_<NAME> environment variables.
_KNOWN_REPOS: Dict[str, RepoSpec] = {
    "ardk": RepoSpec("ardk", url=f"{GITHUB_ORG}/ArDK.git", monorepo_subdir="framework/ardk"),
    "artietool": RepoSpec("artietool", url=f"{GITHUB_ORG}/ArtieTool.git", monorepo_subdir="framework/artietool"),
    "artiecli": RepoSpec("artiecli", url=f"{GITHUB_ORG}/ArtieCLI.git", monorepo_subdir="framework/cli"),
    "artieworkbench": RepoSpec("artieworkbench", url=f"{GITHUB_ORG}/ArtieWorkbench.git", monorepo_subdir="framework/workbench"),
    "artiedaemons": RepoSpec("artiedaemons", url=f"{GITHUB_ORG}/ArtieDaemons.git", monorepo_subdir="framework/daemons"),
    "artie00": RepoSpec("artie00", url=f"{GITHUB_ORG}/Artie00.git", monorepo_subdir="artie00"),
    # Transitional. artie-common's contents (firmware, drivers, schematics) are destined
    # for Artie00; until they move, tasks still need to find them where they are.
    "artie-common": RepoSpec("artie-common", monorepo_subdir="artie-common"),
}


def monorepo_root() -> str:
    """
    Return the absolute path of the root of this repository.

    This is the historical `common.repo_root()`. It stays meaningful only for as long as
    components live in this repo; prefer `repo_path(<name>)` for anything that refers to
    a specific component.
    """
    thisdir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.join(thisdir, "..", "..")
    if not os.path.isdir(root):
        raise FileNotFoundError("The Artie directory seems to have been altered in a way that I can't understand.")

    return os.path.abspath(root)


@dataclasses.dataclass
class Config:
    """
    Resolved Artie Tool workspace configuration.
    """
    workspace: str = str(DEFAULT_WORKSPACE)
    channel: str = "local"
    repos: Dict[str, RepoSpec] = dataclasses.field(default_factory=dict)

    def repo(self, name: str) -> RepoSpec:
        """
        Return the RepoSpec for `name`, raising a helpful error if it is unknown.
        """
        key = name.strip().lower()
        if key not in self.repos:
            known = ", ".join(sorted(self.repos))
            raise KeyError(f"Unknown Artie repository '{name}'. Known repositories: {known}")

        return self.repos[key]

    def repo_path(self, name: str) -> str:
        """
        Return the absolute path of the directory holding `name`'s source.

        Resolution order for a single repo:
          1. an explicit `path` (a development override)
          2. its subdirectory of this monorepo, while it still lives here
          3. a clone under the workspace directory
        """
        spec = self.repo(name)

        if spec.path:
            return os.path.abspath(os.path.expanduser(spec.path))

        if spec.monorepo_subdir:
            candidate = os.path.join(monorepo_root(), spec.monorepo_subdir)
            if os.path.isdir(candidate):
                return os.path.abspath(candidate)

        return os.path.abspath(os.path.join(os.path.expanduser(self.workspace), spec.name))


def _default_repos() -> Dict[str, RepoSpec]:
    return {name: dataclasses.replace(spec) for name, spec in _KNOWN_REPOS.items()}


def _apply_config_file(config: Config, path: pathlib.Path) -> None:
    """
    Overlay settings from a YAML config file onto `config`.
    """
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        raise ValueError(f"Could not read Artie config file {path}: {e}") from e

    if not raw:
        return

    if "workspace" in raw:
        config.workspace = str(raw["workspace"])

    if "channel" in raw:
        config.channel = str(raw["channel"])

    for name, settings in (raw.get("repos") or {}).items():
        key = name.strip().lower()
        spec = config.repos.setdefault(key, RepoSpec(key))
        if not isinstance(settings, dict):
            raise ValueError(f"Config file {path}: repos.{name} should be a mapping, got {type(settings).__name__}")

        for field in ("url", "ref", "path"):
            if settings.get(field) is not None:
                setattr(spec, field, str(settings[field]))


def _apply_environment(config: Config) -> None:
    """
    Overlay settings from environment variables onto `config`.

    ARTIE_WORKSPACE      - the workspace directory
    ARTIE_CHANNEL        - the release channel
    ARTIE_REPO_<NAME>    - a development override path for one repo, where <NAME> is the
                           repo name uppercased with hyphens turned into underscores,
                           e.g. ARTIE_REPO_ARDK or ARTIE_REPO_ARTIE_COMMON
    """
    if os.environ.get("ARTIE_WORKSPACE"):
        config.workspace = os.environ["ARTIE_WORKSPACE"]

    if os.environ.get("ARTIE_CHANNEL"):
        config.channel = os.environ["ARTIE_CHANNEL"]

    for name, spec in config.repos.items():
        env_name = "ARTIE_REPO_" + name.upper().replace("-", "_")
        if os.environ.get(env_name):
            spec.path = os.environ[env_name]


def _apply_args(config: Config, args) -> None:
    """
    Overlay settings from parsed command line arguments onto `config`.
    """
    if getattr(args, "workspace", None):
        config.workspace = args.workspace

    if getattr(args, "channel", None):
        config.channel = args.channel

    for assignment in getattr(args, "repo", None) or []:
        if "=" not in assignment:
            raise ValueError(f"--repo expects <name>=<path>, got '{assignment}'")

        name, _, path = assignment.partition("=")
        key = name.strip().lower()
        spec = config.repos.setdefault(key, RepoSpec(key))
        spec.path = path.strip()


def load(args=None, config_path=None) -> Config:
    """
    Resolve the workspace configuration from defaults, config file, environment and args.
    """
    config = Config(repos=_default_repos())

    path = pathlib.Path(config_path) if config_path else None
    if path is None:
        env_path = os.environ.get("ARTIE_CONFIG")
        path = pathlib.Path(env_path) if env_path else DEFAULT_CONFIG_PATH

    if path.is_file():
        LOGGER.debug(f"Reading Artie config from {path}")
        _apply_config_file(config, path)

    _apply_environment(config)

    if args is not None:
        _apply_args(config, args)

    return config


# Artie Tool runs tasks across several processes, and each one resolves paths. Cache the
# configuration per process so that a config file is not re-read for every substitution.
_CACHED: Optional[Config] = None


def config(args=None) -> Config:
    """
    Return the process-wide resolved configuration, loading it on first use.

    Pass `args` once, early, to fold command line overrides in. Later calls reuse the
    already-resolved configuration.
    """
    global _CACHED

    if _CACHED is None or args is not None:
        _CACHED = load(args)

    return _CACHED


def reset_cache() -> None:
    """
    Drop the cached configuration. Intended for tests.
    """
    global _CACHED
    _CACHED = None


def repo_path(name: str, args=None) -> str:
    """
    Return the absolute path of the directory holding `name`'s source.
    """
    return config(args).repo_path(name)


def known_repo_names() -> List[str]:
    """
    Return the names of every repository Artie Tool knows how to locate.
    """
    return sorted(_KNOWN_REPOS)


def _git(args_list: List[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args_list, cwd=cwd, capture_output=True, text=True)


def _is_git_checkout(path: str) -> bool:
    return os.path.isdir(os.path.join(path, ".git"))


def repo_status(name: str, cfg: Config) -> dict:
    """
    Describe where one repository resolves to and what state it is in.
    """
    spec = cfg.repo(name)
    path = cfg.repo_path(name)
    info = {
        "name": name,
        "path": path,
        "exists": os.path.isdir(path),
        "dev_override": spec.is_dev_override,
        "url": spec.url,
        "ref": spec.ref,
        "git": False,
        "head": None,
        "dirty": None,
    }

    if info["exists"] and _is_git_checkout(path):
        info["git"] = True
        head = _git(["rev-parse", "--short", "HEAD"], cwd=path)
        if head.returncode == 0:
            info["head"] = head.stdout.strip()

        dirty = _git(["status", "--porcelain"], cwd=path)
        if dirty.returncode == 0:
            info["dirty"] = bool(dirty.stdout.strip())

    return info


def sync_repo(name: str, cfg: Config, dry_run: bool = False) -> bool:
    """
    Make sure one repository is present at the configured ref.

    Returns True if the repository is usable afterwards. A repository with an explicit
    `path` is a development override and is left completely alone - that is the point of
    setting one, so that building from source never overwrites work in progress.
    """
    spec = cfg.repo(name)
    path = cfg.repo_path(name)

    if spec.is_dev_override:
        if not os.path.isdir(path):
            LOGGER.error(f"{name}: configured path {path} does not exist")
            return False

        LOGGER.info(f"{name}: using {path} (development override; leaving it untouched)")
        return True

    # Still living in this monorepo - nothing to clone.
    if spec.monorepo_subdir and os.path.isdir(os.path.join(monorepo_root(), spec.monorepo_subdir)):
        LOGGER.info(f"{name}: using {path} (still part of this repository)")
        return True

    if os.path.isdir(path):
        if not _is_git_checkout(path):
            LOGGER.error(f"{name}: {path} exists but is not a git checkout; refusing to touch it")
            return False

        LOGGER.info(f"{name}: fetching {spec.ref} in {path}")
        if dry_run:
            return True

        fetch = _git(["fetch", "--tags", "origin"], cwd=path)
        if fetch.returncode != 0:
            LOGGER.error(f"{name}: git fetch failed: {fetch.stderr.strip()}")
            return False

        checkout = _git(["checkout", spec.ref], cwd=path)
        if checkout.returncode != 0:
            LOGGER.error(f"{name}: git checkout {spec.ref} failed: {checkout.stderr.strip()}")
            return False

        return True

    if not spec.url:
        LOGGER.error(f"{name}: no local checkout at {path} and no clone URL configured")
        return False

    LOGGER.info(f"{name}: cloning {spec.url} ({spec.ref}) into {path}")
    if dry_run:
        return True

    os.makedirs(os.path.dirname(path), exist_ok=True)
    clone = _git(["clone", "--branch", spec.ref, spec.url, path], cwd=os.path.dirname(path))
    if clone.returncode != 0:
        LOGGER.error(f"{name}: git clone failed: {clone.stderr.strip()}")
        return False

    return True
