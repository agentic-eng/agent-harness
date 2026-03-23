.PHONY: lint fix test audit

lint:
	agent-harness lint

fix:
	agent-harness fix

test:
	uv run pytest tests/ -v
	conftest verify -p policies/ --no-color

audit:
	agent-harness audit
