from git_sync_filtered.__main__ import collect_paths_to_keep


def test_collect_paths_to_keep_from_args():
    result = collect_paths_to_keep(keep=("src", "docs"), keep_from_file=None)
    assert result == ["docs", "src"]


def test_collect_paths_to_keep_combines_args_and_file(tmp_path):
    file_path = tmp_path / "paths.txt"
    file_path.write_text("tests\nlib\n")

    result = collect_paths_to_keep(
        keep=("src",),
        keep_from_file=str(file_path),
    )

    assert result == ["lib", "src", "tests"]


def test_collect_paths_to_keep_removes_duplicates():
    result = collect_paths_to_keep(keep=("src", "docs", "src"), keep_from_file=None)

    assert result == ["docs", "src"]


def test_collect_paths_to_keep_keeps_first_occurrence():
    result = collect_paths_to_keep(
        keep=("src", "docs", "src", "tests"),
        keep_from_file=None,
    )

    assert result == ["docs", "src", "tests"]
