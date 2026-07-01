from pathlib import Path

import pytest

from pytale_tools.builder.req_parser import Requirement, parse_requirements


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content)
    return p


def test_basic_pinned(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo==1.0.0\n")
    assert parse_requirements(p) == [Requirement("foo", "1.0.0")]


def test_multiple_packages(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo==1.0\nbar==2.3.1\n")
    result = parse_requirements(p)
    assert result == [Requirement("foo", "1.0"), Requirement("bar", "2.3.1")]


def test_comments_and_blank_lines(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "# header\n\nfoo==1.0\n\n# footer\n")
    assert parse_requirements(p) == [Requirement("foo", "1.0")]


def test_inline_comment(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo==1.0  # some note\n")
    assert parse_requirements(p) == [Requirement("foo", "1.0")]


def test_extras_ignored(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo[bar,baz]==1.0\n")
    assert parse_requirements(p) == [Requirement("foo", "1.0")]


def test_line_continuation(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo==\\\n1.0\n")
    assert parse_requirements(p) == [Requirement("foo", "1.0")]


def test_environment_marker_stripped(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", 'foo==1.0; python_version >= "3.12"\n')
    assert parse_requirements(p) == [Requirement("foo", "1.0")]


def test_recursive_include(tmp_path: Path) -> None:
    _write(tmp_path, "base.txt", "foo==1.0\n")
    p = _write(tmp_path, "r.txt", "-r base.txt\nbar==2.0\n")
    result = parse_requirements(p)
    assert result == [Requirement("foo", "1.0"), Requirement("bar", "2.0")]


def test_error_unpinned_gte(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo>=1.0\n")
    with pytest.raises(ValueError, match="Only pinned versions"):
        parse_requirements(p)


def test_error_unpinned_compatible(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo~=1.0\n")
    with pytest.raises(ValueError, match="Only pinned versions"):
        parse_requirements(p)


def test_error_no_version(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo\n")
    with pytest.raises(ValueError, match="Version must be pinned"):
        parse_requirements(p)


def test_editable_with_pyproject(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "pyproject.toml").write_text(
        '[project]\nname = "my-pkg"\nversion = "1.2.3"\n'
    )
    p = _write(tmp_path, "r.txt", f"-e {pkg_dir}\n")
    result = parse_requirements(p)
    assert len(result) == 1
    assert result[0].name == "my_pkg"
    assert result[0].version == "1.2.3"
    assert result[0].path == pkg_dir
    assert result[0].is_editable is True


def test_editable_without_pyproject(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "some_lib"
    pkg_dir.mkdir()
    p = _write(tmp_path, "r.txt", f"-e {pkg_dir}\n")
    result = parse_requirements(p)
    assert result[0].name == "some_lib"
    assert result[0].version == "0.0.0"
    assert result[0].is_editable is True


def test_editable_relative_path(tmp_path: Path) -> None:
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "pyproject.toml").write_text(
        '[project]\nname = "mypkg"\nversion = "0.1.0"\n'
    )
    p = _write(tmp_path, "r.txt", "-e ./mypkg\n")
    result = parse_requirements(p)
    assert result[0].is_editable is True
    assert result[0].path == pkg_dir.resolve()


def test_editable_missing_path(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "-e ./nonexistent\n")
    with pytest.raises(FileNotFoundError, match="Editable install path not found"):
        parse_requirements(p)


def test_error_url_requirement(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo @ https://example.com/foo.whl\n")
    with pytest.raises(ValueError, match="URL requirements"):
        parse_requirements(p)


def test_error_conflicting_versions(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo==1.0\nfoo==2.0\n")
    with pytest.raises(ValueError, match="Conflicting versions"):
        parse_requirements(p)


def test_error_circular_include(tmp_path: Path) -> None:
    _write(tmp_path, "a.txt", "-r b.txt\n")
    _write(tmp_path, "b.txt", "-r a.txt\n")
    with pytest.raises(ValueError, match="Circular"):
        parse_requirements(tmp_path / "a.txt")


def test_empty_file(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "")
    assert parse_requirements(p) == []


def test_pip_options_ignored(tmp_path: Path) -> None:
    p = _write(
        tmp_path, "r.txt", "--find-links ./wheels\n--index-url https://x\nfoo==1.0\n"
    )
    assert parse_requirements(p) == [Requirement("foo", "1.0")]


def test_name_normalization(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "Foo-Bar==1.0\n")
    assert parse_requirements(p) == [Requirement("foo_bar", "1.0")]


def test_name_normalization_dots(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo.bar==1.0\n")
    assert parse_requirements(p) == [Requirement("foo_bar", "1.0")]


def test_deduplication(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo==1.0\nfoo==1.0\n")
    assert parse_requirements(p) == [Requirement("foo", "1.0")]


def test_requirement_flag_long_form(tmp_path: Path) -> None:
    _write(tmp_path, "base.txt", "foo==1.0\n")
    p = _write(tmp_path, "r.txt", "--requirement base.txt\nbar==2.0\n")
    result = parse_requirements(p)
    assert result == [Requirement("foo", "1.0"), Requirement("bar", "2.0")]


def test_whitespace_around_operator(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "foo == 1.0\n")
    assert parse_requirements(p) == [Requirement("foo", "1.0")]


def test_local_wheel_path(tmp_path: Path) -> None:
    whl = tmp_path / "foo-1.0.0-py3-none-any.whl"
    whl.write_bytes(b"")
    p = _write(tmp_path, "r.txt", "./foo-1.0.0-py3-none-any.whl\n")
    result = parse_requirements(p)
    assert result == [Requirement("foo", "1.0.0", path=whl.resolve())]


def test_local_wheel_mixed_with_pypi(tmp_path: Path) -> None:
    whl = tmp_path / "local_pkg-0.1.0-py3-none-any.whl"
    whl.write_bytes(b"")
    p = _write(tmp_path, "r.txt", "./local_pkg-0.1.0-py3-none-any.whl\nremote==2.0\n")
    result = parse_requirements(p)
    assert result[0] == Requirement("local_pkg", "0.1.0", path=whl.resolve())
    assert result[1] == Requirement("remote", "2.0")


def test_local_wheel_not_found(tmp_path: Path) -> None:
    p = _write(tmp_path, "r.txt", "./missing-1.0.0-py3-none-any.whl\n")
    with pytest.raises(FileNotFoundError, match="Local wheel not found"):
        parse_requirements(p)


def test_local_wheel_name_normalization(tmp_path: Path) -> None:
    whl = tmp_path / "Foo_Bar-1.0.0-py3-none-any.whl"
    whl.write_bytes(b"")
    p = _write(tmp_path, "r.txt", "./Foo_Bar-1.0.0-py3-none-any.whl\n")
    result = parse_requirements(p)
    assert result[0].name == "foo_bar"
