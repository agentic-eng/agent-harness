from agent_harness.workspace import discover_roots


def test_discover_single_root(tmp_path):
    (tmp_path / ".agent-harness.yml").write_text("stacks: [python]")
    roots = discover_roots(tmp_path)
    assert roots == [tmp_path]


def test_discover_subprojects(tmp_path):
    (tmp_path / ".agent-harness.yml").write_text("stacks: [docker]")
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / ".agent-harness.yml").write_text("stacks: [python]")
    roots = discover_roots(tmp_path)
    assert tmp_path in roots
    assert backend in roots


def test_discover_skips_excluded_dirs(tmp_path):
    (tmp_path / ".agent-harness.yml").write_text("stacks: [python]")
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / ".agent-harness.yml").write_text("stacks: [python]")
    node = tmp_path / "node_modules"
    node.mkdir()
    (node / ".agent-harness.yml").write_text("stacks: [javascript]")
    roots = discover_roots(tmp_path)
    assert len(roots) == 1
    assert roots[0] == tmp_path


def test_discover_nested_services(tmp_path):
    services = tmp_path / "services"
    auth = services / "auth"
    billing = services / "billing"
    auth.mkdir(parents=True)
    billing.mkdir(parents=True)
    (auth / ".agent-harness.yml").write_text("stacks: [python]")
    (billing / ".agent-harness.yml").write_text("stacks: [python]")
    roots = discover_roots(tmp_path)
    assert auth in roots
    assert billing in roots


def test_discover_no_dotfiles(tmp_path):
    roots = discover_roots(tmp_path)
    assert roots == []
