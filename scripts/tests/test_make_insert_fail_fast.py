#!/usr/bin/env python3
"""ROM-free tests for make.py subprocess failure propagation."""
import importlib.util
import io
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import call, mock_open, patch


ROOT = Path(__file__).resolve().parents[2]
MAKE_PATH = ROOT / "scripts" / "make.py"
spec = importlib.util.spec_from_file_location("cfru_make_fail_fast", MAKE_PATH)
make = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make)


def require(condition, message):
    if not condition:
        raise AssertionError("make.py fail-fast regression: " + message)


def with_fake_rom_open():
    return patch("builtins.open", mock_open())


def test_insert_success():
    with patch.object(make.shutil, "which", return_value="synthetic-python"), \
            patch.object(make.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)) as run:
        make.InsertCode()
    require(run.call_args == call(["python3", "scripts/insert.py"], check=True),
            "successful insert did not use checked subprocess execution")


def test_insert_nonzero_fails():
    failure = subprocess.CalledProcessError(7, ["python3", "scripts/insert.py"])
    with patch.object(make.shutil, "which", return_value="synthetic-python"), \
            patch.object(make.subprocess, "run", side_effect=failure):
        try:
            make.InsertCode()
        except subprocess.CalledProcessError as error:
            require(error.returncode == 7, "insert exit code was not propagated")
        else:
            raise AssertionError("make.py fail-fast regression: non-zero insert reported success")


def test_execution_error_fails():
    stderr = io.StringIO()
    with patch.object(make.shutil, "which", return_value="synthetic-python"), \
            patch.object(make.subprocess, "run", side_effect=OSError("synthetic execution failure")), \
            patch("sys.stderr", stderr):
        try:
            make.InsertCode()
        except SystemExit as error:
            require(error.code == 1, "insert execution error did not produce failure status")
        else:
            raise AssertionError("make.py fail-fast regression: execution error reported success")


def test_build_nonzero_fails_make():
    old_rom_name = make.ROM_NAME
    make.ROM_NAME = "synthetic-source-fixture"
    try:
        with with_fake_rom_open(), \
                patch.object(make, "EditLinker"), patch.object(make, "EditInsert"), \
                patch.object(make.shutil, "which", return_value="synthetic-python"), \
                patch.object(make.subprocess, "run",
                             side_effect=subprocess.CalledProcessError(9, ["python3", "scripts/build.py"])):
            try:
                make.main()
            except subprocess.CalledProcessError as error:
                require(error.returncode == 9, "build exit code was not propagated")
            else:
                raise AssertionError("make.py fail-fast regression: failed build reported success")
    finally:
        make.ROM_NAME = old_rom_name


def test_build_and_insert_success():
    old_rom_name = make.ROM_NAME
    make.ROM_NAME = "synthetic-source-fixture"
    try:
        with with_fake_rom_open(), \
                patch.object(make, "EditLinker"), patch.object(make, "EditInsert"), \
                patch.object(make.shutil, "which", return_value="synthetic-python"), \
                patch.object(make.subprocess, "run",
                             side_effect=[subprocess.CompletedProcess([], 0),
                                          subprocess.CompletedProcess([], 0)]) as run:
            make.main()
        require(run.call_args_list == [
            call(["python3", "scripts/build.py"], check=True),
            call(["python3", "scripts/insert.py"], check=True),
        ], "successful make did not require both checked stages")
    finally:
        make.ROM_NAME = old_rom_name


def test_stale_output_cannot_mask_failed_insert():
    old_rom_name = make.ROM_NAME
    sentinel = b"stale synthetic output fixture; not a ROM\n"
    try:
        with tempfile.TemporaryDirectory(prefix="cfru-make-stale-output-") as temp:
            stale_output = Path(temp) / "test.gba"
            stale_output.write_bytes(sentinel)
            make.ROM_NAME = str(stale_output)
            with patch.object(make, "EditLinker"), patch.object(make, "EditInsert"), \
                    patch.object(make.shutil, "which", return_value="synthetic-python"), \
                    patch.object(make.subprocess, "run",
                                 side_effect=[subprocess.CompletedProcess([], 0),
                                              subprocess.CalledProcessError(
                                                  11, ["python3", "scripts/insert.py"])]):
                try:
                    make.main()
                except subprocess.CalledProcessError as error:
                    require(error.returncode == 11, "failed insert exit code was not propagated")
                else:
                    raise AssertionError("make.py fail-fast regression: stale output masked failed insert")
            require(stale_output.read_bytes() == sentinel,
                    "synthetic stale output fixture was changed during failed insertion")
    finally:
        make.ROM_NAME = old_rom_name


def main():
    tests = (
        test_insert_success,
        test_insert_nonzero_fails,
        test_execution_error_fails,
        test_build_nonzero_fails_make,
        test_build_and_insert_success,
        test_stale_output_cannot_mask_failed_insert,
    )
    for test in tests:
        test()
        print("PASS: " + test.__name__)
    print("make.py fail-fast regression suite: PASS (6/6)")


if __name__ == "__main__":
    main()
