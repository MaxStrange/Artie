"""
Helper script to prepare Helm charts with dependencies before deployment.

This script runs 'helm dependency update' for charts that have dependencies,
ensuring that dependent charts (like artie-base) are properly pulled in
before deployment.
"""
import subprocess
import sys
import pathlib


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
            print(f"✓ Successfully updated dependencies for {chart_path.name}")
            return True
        else:
            print(f"✗ Failed to update dependencies for {chart_path.name}")
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
    
    # Charts that have dependencies
    dependent_charts = ["artie00"]
    
    success = True
    for chart_name in dependent_charts:
        chart_path = deploy_files_dir / chart_name
        
        if not chart_path.exists():
            print(f"Warning: Chart directory {chart_path} not found, skipping...")
            continue
        
        # Check if Chart.yaml has dependencies
        chart_yaml = chart_path / "Chart.yaml"
        if not chart_yaml.exists():
            print(f"Warning: {chart_yaml} not found, skipping...")
            continue
        
        # Update dependencies
        if not update_chart_dependencies(chart_path):
            success = False
    
    if success:
        print("\n✓ All chart dependencies updated successfully!")
        sys.exit(0)
    else:
        print("\n✗ Some chart dependencies failed to update.")
        sys.exit(1)


if __name__ == "__main__":
    main()
