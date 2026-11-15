from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START_BAT = (ROOT / "start.bat").read_text(encoding="utf-8")
BUILD_BAT = (ROOT / "build_windows_exe.bat").read_text(encoding="utf-8")


def test_startup_refreshes_dependencies_when_upgrading_to_current_version():
    assert '".venv\\.spaceline_ready_0.9.6"' in START_BAT
    assert 'echo ready>".venv\\.spaceline_ready_0.9.6"' in START_BAT


def test_windows_exe_builder_installs_dev_dependencies_and_runs_full_pytest_suite():
    assert "-r requirements-dev.txt" in BUILD_BAT
    assert "python -m pytest -q" in BUILD_BAT


def test_windows_launcher_checks_for_chromium_and_installs_it_when_missing():
    assert "playwright.sync_api" in START_BAT
    assert "p.chromium.executable_path" in START_BAT
    assert "python -m playwright install chromium" in START_BAT
    assert "Chromium is missing" in START_BAT
    assert "Spaceline can still start" in START_BAT


def test_application_reports_current_version():
    main_py = (ROOT / "app" / "main.py").read_text(encoding="utf-8")
    version_py = (ROOT / "app" / "version.py").read_text(encoding="utf-8")
    assert "from app.version import APP_VERSION" in main_py
    assert 'APP_VERSION = "0.9.6"' in version_py


def test_startup_marker_is_versioned_for_current_release():
    assert '.spaceline_ready_0.9.6' in START_BAT


def test_launcher_chooses_an_available_loopback_port_instead_of_reusing_a_stale_server():
    from run import choose_port
    import socket

    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    occupied = blocker.getsockname()[1]
    try:
        selected = choose_port(start_port=occupied, end_port=occupied + 1)
        assert selected == occupied + 1
    finally:
        blocker.close()


def test_launcher_fails_clearly_when_no_local_port_is_available():
    from run import choose_port
    import socket

    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    blocker.bind(("127.0.0.1", 0))
    blocker.listen(1)
    occupied = blocker.getsockname()[1]
    try:
        try:
            choose_port(start_port=occupied, end_port=occupied)
        except RuntimeError as exc:
            assert "No available local port" in str(exc)
        else:
            raise AssertionError("choose_port should fail when its only candidate is occupied")
    finally:
        blocker.close()
