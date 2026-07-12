import stat

from secure_files import write_private_text


def test_private_file_is_created_with_owner_only_permissions(tmp_path) -> None:
    target = tmp_path / "nested" / "token.json"
    write_private_text(target, "secret")
    assert target.read_text() == "secret"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_private_file_replacement_keeps_owner_only_permissions(tmp_path) -> None:
    target = tmp_path / "state.json"
    target.write_text("old")
    target.chmod(0o644)
    write_private_text(target, "new")
    assert target.read_text() == "new"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
