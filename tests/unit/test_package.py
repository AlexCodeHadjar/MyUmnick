import vtuber


def test_package_exposes_installed_version() -> None:
    assert vtuber.__version__ == "0.1.0"
