.PHONY: bootstrap check test production lock
bootstrap:
	./scripts/bootstrap.sh
check:
	./scripts/check.sh
test:
	./scripts/test.sh
production: check
	.venv/bin/python scripts/gates.py --production
lock:
	.venv/bin/python -m piptools compile --allow-unsafe --generate-hashes --output-file requirements-dev.lock requirements-dev.in
