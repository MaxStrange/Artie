"""
Helper to prepare Helm charts with dependencies before deployment.

Runs 'helm dependency update' for every chart in the workspace that declares
dependencies, so that any subcharts are pulled in before deployment.

Run it as a module from the framework directory, since it is part of the artietool
package:

    python -m artietool.update_chart_dependencies
"""
import subprocess
import sys
import pathlib
import yaml

from . import workspace


def update_chart_dependencies(chart_path: pathlib.Path) -> bool:
    """
    Update dependencies for a Helm chart.
    
    Args:
        chart_path: Path to the Helm chart directory
        
    Returns:
        True if successful, False otherwise
    """
    print(f"Updating dependencies for {chart_path.name}...")
    
    try:
        result = subprocess.run(
            ["helm", "dependency", "update", str(chart_path)],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            print(f"[OK] Successfully updated dependencies for {chart_path.name}")
            return True
        else:
            print(f"[FAIL] Failed to update dependencies for {chart_path.name}")
            print(f"Error: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("Error: 'helm' command not found. Please install Helm.")
        return False
    except Exception as e:
        print(f"Error updating dependencies: {e}")
        return False


def find_charts() -> list:
    """
    Return every Helm chart in the workspace.

    Each component ships the chart that deploys it, in its own 'deploy' directory, so
    this looks across all the components rather than at one shared directory.
    """
    charts = []
    for repo in workspace.known_repo_names():
        deploy_dir = pathlib.Path(workspace.repo_path(repo)) / "deploy"
        if deploy_dir.is_dir():
            charts.extend(sorted(deploy_dir.glob("*/Chart.yaml")))

    return charts


def main():
    """Main entry point."""
    # Find the charts that actually declare dependencies, rather than hard-coding a
    # list. Charts that need a 'helm dependency update' are discovered from their
    # Chart.yaml, wherever in the workspace they live.
    dependent_charts = []
    for chart_yaml in find_charts():
        try:
            chart = yaml.safe_load(chart_yaml.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as e:
            print(f"Warning: could not read {chart_yaml}: {e}, skipping...")
            continue

        if chart and chart.get("dependencies"):
            dependent_charts.append(chart_yaml.parent)

    if not dependent_charts:
        print("No charts declare dependencies; nothing to update.")

    success = True
    for chart_path in dependent_charts:
        # Update dependencies
        if not update_chart_dependencies(chart_path):
            success = False
    
    if success:
        print("\n[OK] All chart dependencies updated successfully!")
        sys.exit(0)
    else:
        print("\n[FAIL] Some chart dependencies failed to update.")
        sys.exit(1)


if __name__ == "__main__":
    main()
