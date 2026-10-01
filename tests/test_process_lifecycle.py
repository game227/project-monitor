import time

import psutil

from app.process.process_manager import InvalidCommandError, ProcessManager

_RELOADER_SCRIPT = """
import signal, subprocess, sys, time

# Mimics Django's runserver / Flask's debug reloader: a parent process
# that spawns the actual server as a child in the same process group,
# and itself dies quickly on SIGTERM without forwarding it -- exactly
# the shape that left a real Django dev server running after "Stop".
child = subprocess.Popen([sys.executable, "-c",
    "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"])
with open(sys.argv[1], "w") as f:
    f.write(str(child.pid))
signal.signal(signal.SIGTERM, signal.SIG_DFL)
time.sleep(60)
"""


def test_start_and_stop(tmp_path) -> None:
    manager = ProcessManager()
    manager.start("sleep 30", str(tmp_path))

    assert manager.is_running is True
    assert manager.pid is not None

    manager.stop()
    time.sleep(0.2)
    assert manager.is_running is False


def test_process_exits_on_its_own(tmp_path) -> None:
    manager = ProcessManager()
    manager.start("true", str(tmp_path))
    for _ in range(20):
        if not manager.is_running:
            break
        time.sleep(0.1)
    assert manager.is_running is False


def test_empty_command_is_rejected(tmp_path) -> None:
    manager = ProcessManager()
    try:
        manager.start("   ", str(tmp_path))
    except InvalidCommandError:
        pass
    else:
        raise AssertionError("expected InvalidCommandError")


def test_stop_kills_a_reloader_style_grandchild(tmp_path) -> None:
    script = tmp_path / "reloader.py"
    script.write_text(_RELOADER_SCRIPT)
    child_pid_file = tmp_path / "child_pid.txt"

    manager = ProcessManager()
    manager.start(f"python3 {script} {child_pid_file}", str(tmp_path))
    parent_pid = manager.pid

    for _ in range(50):
        if child_pid_file.exists():
            break
        time.sleep(0.1)
    child_pid = int(child_pid_file.read_text())
    assert psutil.pid_exists(child_pid)

    manager.stop()
    time.sleep(0.5)

    assert not psutil.pid_exists(parent_pid), "reloader process should be gone"
    assert not psutil.pid_exists(child_pid), "the server it spawned should be gone too"


def test_cannot_start_twice(tmp_path) -> None:
    manager = ProcessManager()
    manager.start("sleep 30", str(tmp_path))
    try:
        manager.start("sleep 30", str(tmp_path))
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")
    finally:
        manager.stop()
