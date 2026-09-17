# %% [markdown]
# ## Full pipeline
#
# Run the Bronze, Silver, and Gold layers in dependency order.

# %%
from pathlib import Path
import subprocess
import sys


TRANSFORMATIONS_DIR = Path(__file__).resolve().parent

PIPELINE_SCRIPTS = [
    "extract_bronze.py",
    "transform_silver.py",
    "transform_gold.py",
]


def run_pipeline_script(script_name: str) -> None:
    """Run one pipeline stage with the active Python interpreter."""
    script_path = TRANSFORMATIONS_DIR / script_name

    if not script_path.exists():
        raise FileNotFoundError(f"Pipeline script not found: {script_path}")

    print(
        f"\n{'=' * 72}\nRunning {script_name}\n{'=' * 72}",
        flush=True,
    )
    subprocess.run(
        [sys.executable, str(script_path)],
        check=True,
    )


def main() -> None:
    """Run every pipeline layer, stopping when a stage fails."""
    for script_name in PIPELINE_SCRIPTS:
        run_pipeline_script(script_name)

    print("\nFull Bronze-to-Gold pipeline completed successfully.", flush=True)


if __name__ == "__main__":
    main()
