"""
Write the README for each extracted component repository.

Called by split-repos.sh. Kept separate so the READMEs are easy to read and edit
without wading through shell quoting.
"""
import pathlib
import sys

HUB = "https://github.com/ArtieBots/Artie"

READMES = {
    "ArDK": (
        "The Artie Development Kit",
        """Libraries, services, base Docker images and firmware libraries for the Artie
developmental robotics platform. This is what you build an Artie application or a
driver *on top of*.

- `libraries/` - the Python libraries: `artie-util`, `artie-i2c`, `artie-gpio`,
  `artie-can`, `artie-service-client`, `artie-tooling`
- `services/` - the platform services: API server, RPC broker, pub/sub broker, telemetry
- `base-image/` - the `artie-base` Docker image that Artie containers derive from
- `firmware/libraries/` - reusable Pico firmware libraries (`leds`, `errors`, `cmds`)
- `deploy/artie-base/` - the Helm chart that deploys the platform services""",
    ),
    "ArtieTool": (
        "Build system, test harness and deployment tool for Artie",
        """Artie Tool builds, tests, flashes and deploys every Artie component. It locates each
component through a workspace configuration rather than assuming they share a
directory, so the components can live in separate repositories.

```bash
pip install artietool
artie-tool workspace status   # where each component resolves to
artie-tool workspace sync     # clone or fetch them
artie-tool build all
```

See [TASKS.md](./artietool/TASKS.md) for the task definition format.""",
    ),
    "ArtieCLI": (
        "Command line interface for a running Artie",
        """`artie-cli` talks to an Artie's services directly. It is used for automated testing
of the micro-services, and for poking at hardware from a shell on the controller node.

```bash
pip install artiecli
artie-cli --help
```""",
    ),
    "ArtieWorkbench": (
        "Graphical interface for configuring and controlling an Artie",
        """Artie Workbench is the application most people use to set up, deploy to, and drive
an Artie. It uses Artie Tool underneath.

```bash
pip install artieworkbench
artie-workbench
```

Licensed LGPL-3.0-or-later - see [License](./License). The rest of the Artie ecosystem
is MIT.""",
    ),
    "ArtieDaemons": (
        "Host daemons for an Artie Kubernetes cluster",
        """Install scripts and systemd units for the nodes that host an Artie's k3s cluster.

- `artie-admind/` - the k3s server (admin node)
- `artie-computed/` - a k3s agent (compute node)""",
    ),
    "Artie00": (
        "Artie00 - an Artie that simulates a newborn infant",
        """Everything specific to Artie00: its hardware manifest, bill of materials, MCU
firmware, user-space drivers, electrical schematics, and the Helm chart that deploys it.

- `artie00.yml` - the hardware manifest
- `bom.md` - bill of materials
- `firmware/` - MCU firmware (Pico, C)
- `drivers/` - user-space driver applications
- `electrical-schematics/` - KiCad schematics and gerbers, covered by
  [HW-LICENSE](./HW-LICENSE)
- `deploy/artie00/` - the Helm chart""",
    ),
}


def _existing_body(readme: pathlib.Path) -> str:
    """
    Return the useful part of a README the component already had, without its title.

    The components carried their own READMEs in the monorepo, some with things that
    exist nowhere else - ArtieCLI's, for instance, documents an Ubuntu install
    workaround. Overwriting them wholesale would drop that, so keep it below the new
    overview instead.
    """
    if not readme.is_file():
        return ""

    lines = readme.read_text(encoding="utf-8").splitlines()
    # Drop a leading '# Title' and any blank lines after it; the new README has its own.
    while lines and (not lines[0].strip() or lines[0].startswith("# ")):
        lines.pop(0)

    return "\n".join(lines).strip()


def main(workspace: str) -> int:
    ws = pathlib.Path(workspace)
    for name, (tagline, body) in READMES.items():
        target = ws / name
        if not target.is_dir():
            print(f"  skipping {name}: {target} does not exist")
            continue

        readme = target / "README.md"
        previous = _existing_body(readme)
        carried_over = f"\n---\n\n{previous}\n" if previous else ""

        readme.write_text(
            f"# {name}\n\n{tagline}.\n\n{body}\n\n"
            "## About Artie\n\n"
            "Artie is an open source developmental robotics platform. The documentation,\n"
            "the getting started guide and the architecture overview live in the main\n"
            f"repository: {HUB}\n\n"
            "This repository was split out of that one; its history is preserved.\n"
            f"{carried_over}",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else str(pathlib.Path.home() / "artie-workspace")))
