from pathlib import Path

from tests.run_all_tests import SUITE_TARGETS, build_pytest_args


def test_named_quality_suites_resolve_to_existing_unique_test_files():
    tests_dir = Path(__file__).parent
    for suite, test_files in SUITE_TARGETS.items():
        assert test_files, suite
        assert len(test_files) == len(set(test_files)), suite
        assert all((tests_dir / test_file).is_file() for test_file in test_files), suite
        assert build_pytest_args(str(tests_dir), suite)[-1] == "-q"


def test_full_suite_keeps_pytest_collection_root():
    tests_dir = Path(__file__).parent
    assert build_pytest_args(str(tests_dir), "full") == [str(tests_dir), "-q"]
