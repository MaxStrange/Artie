"""
Helper script to prepare Helm charts with dependencies before deployment.

This script runs 'helm dependency update' for charts that have dependencies,
ensuring that dependent charts (like artie-base) are properly pulled in
before deployment.
"""
import subprocess
import sys
import pathlib
import yaml


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


def main():
    """Main entry point."""
    # Get the deploy-files directory
    script_dir = pathlib.Path(__file__).parent
    deploy_files_dir = script_dir / "deploy-files"
    
    if not deploy_files_dir.exists():
        print(f"Error: deploy-files directory not found at {deploy_files_dir}")
        sys.exit(1)
    
    # Find the charts that actually declare dependencies, rather than hard-coding a
    # list. As charts move out to their own repositories, whichever ones need a
    # 'helm dependency update' should be discovered from their Chart.yaml.
    dependent_charts = []
    for chart_yaml in sorted(deploy_files_dir.glob("*/Chart.yaml")):
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
