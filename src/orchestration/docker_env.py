from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid

from src.models.input_data_models import SWEBenchTaskInput


def ensure_image(image: str) -> None:
    """Pull the Docker image only if it is not already present locally."""
    inspect_res = subprocess.run(
        ["docker", "image", "inspect", image],
        capture_output=True,
        text=True,
    )
    if inspect_res.returncode != 0:
        subprocess.run(
            ["docker", "pull", image],
            stdout=sys.stderr,
            stderr=sys.stderr,
            check=True,
        )


def extract_testbed(image: str, host_dir: Path) -> None:
    """Copy /testbed contents (including .git) from image into host_dir."""
    tmp_name = f"testbed-container-init-{uuid.uuid4().hex[:6]}"
    try:
        subprocess.run(
            ["docker", "create", "--name", tmp_name, image],
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["docker", "cp", f"{tmp_name}:/testbed/.", str(host_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
    finally:
        subprocess.run(
            ["docker", "rm", "-f", tmp_name],
            capture_output=True,
        )


@contextmanager
def swe_docker_env(
    task: SWEBenchTaskInput
) -> Generator[tuple[str, str], None, None]:
    """Prepare shared host testbed and running container for SWE-bench.

    Yields:
        A tuple (container_id, host_temp_dir) and guarantees cleanup
        of both the container and temporary directory on exit or SIGTERM.
    """
    # Create testbed outside current repo for security and .git conflicts
    host_dir = Path(tempfile.mkdtemp(prefix="smith_testbed_")).resolve()
    container_name = f"agent-container-{uuid.uuid4().hex[:6]}"
    container_id: str | None = None
    prev_sigterm = signal.getsignal(signal.SIGTERM)

    # "frame" is useless but mandatory with the signal signature
    def handle_sigterm(signum: int, frame: Any) -> None:
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, handle_sigterm)
    try:
        ensure_image(task.docker_image)
        extract_testbed(task.docker_image, host_dir)

        # write task eval script into eval.sh
        eval_path = host_dir / "eval.sh"
        eval_path.write_text(
            # to avoid crash from Windows to Linux
            task.eval_script.replace("\r\n", "\n"),
            encoding="utf-8",
        )
        os.chmod(eval_path, 0o755)

        run_res = subprocess.run(
            [
                "docker", "run", "-d",
                "--name", container_name,
                "-v", f"{host_dir}:/testbed",
                task.docker_image,
                "tail", "-f", "/dev/null",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        container_id = run_res.stdout.strip() or container_name

        # go in the container to add the repertory into the safe ones
        # to resolve git Users conflicts (Docker root vs current user)
        # between container and testbed
        subprocess.run(
            [
                "docker", "exec", container_id,
                "git", "config", "--global",
                "--add", "safe.directory", "/testbed",
            ],
            capture_output=True,
        )
        # Pause during the agent do complete_task(), assuring the "finally"
        yield container_id, str(host_dir)
    finally:
        signal.signal(signal.SIGTERM, prev_sigterm)
        subprocess.run(
            ["docker", "rm", "-f", container_id or container_name],
            capture_output=True,
        )
        shutil.rmtree(host_dir, ignore_errors=True)
