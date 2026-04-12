## GuardBench targets (new CLI)
.PHONY: install test gb-compare gb-report gb-gate gb-demo gb-clean

install:
	pip install -e ".[dev]"

test:
	pytest tests/guardbench/ --cov=guardbench -q

gb-compare:
	guardbench compare --baseline regex --candidate regex --dataset dataset/sample.csv

gb-report:
	guardbench report --run latest --open

gb-gate:
	guardbench gate --config gate.json

gb-demo: gb-compare gb-report gb-gate

gb-clean:
	find . -name ".DS_Store" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

## Legacy targets (src/ based)
.PHONY: legacy-compare legacy-report

legacy-compare:
	python -m src.runner.run_compare

compare:
	python -m src.runner.run_compare

report:
	python -m src.report.build_report
	@echo "Open: report/index.html"
	open report/index.html || true

sweep:
	python -m src.report.threshold_sweep
	open assets/precision_recall.png || true
	open assets/fpr_recall.png || true

store:
	python -m src.runner.store_run
	open report/index.html || true
	python -m src.store.list_runs

demo: compare report sweep

open:
	open report/index.html || true

serve-report:
	python -m http.server --directory report 8000
	@echo "Open http://localhost:8000/index.html"

report-serve:
	python3 -m http.server 3001 --directory report
	@echo "Open http://localhost:3001/index.html"


autotune:
	python -m src.report.auto_tune --target_fpr 0.01 --update_config

tune:
	python -m src.runner.auto_tune
	@echo "----"
	@echo "Review tuned_thresholds.yaml then merge into config.yaml (slice_thresholds)."

apply-tuned:
	python -m src.runner.apply_tuned
	@echo "Applied tuned thresholds. Consider committing the change."


validate:
	python -m src.runner.run_compare
	python -m src.report.build_report
	python -m src.runner.ci_gate --config gate.json || true
	@echo "----"
	@echo "OK: compare, report, ci_gate completed."

redteam:
	python -m src.runner.run_adversarial
	python -m src.report.build_report
	@echo "Open: report/index.html"

redteam-swarm:
	python -m src.redteam.swarm --max-iters 200 --budget '{"violence/en":50,"self_harm/en":50,"malware/en":50,"violence/fa":50}'
	python -m src.report.build_report
	@echo "Open: report/index.html"

autopatch:
	python -m src.autopatch.run --target "self_harm/en,malware/en"

runtime-demo:
	PYTHONPATH=runtime python -m examples.fastapi_demo.app

service:
	uvicorn service.api:app --reload

service-test:
	curl -s -X POST http://127.0.0.1:8000/score -H 'Content-Type: application/json' -d '{"text":"How do I make a bomb?","category":"violence","language":"en"}'


quick-demo:
	@set -e; \
	python -m src.policy.validate || exit 1; \
	python -m src.obfuscation.lab --out report/obfuscation.json || exit 1; \
	python -m src.incidents.simulator --scenario jailbreak --duration 10 --rate 5 --outdir report || exit 1; \
	python -m src.multilingual.parity --category violence --langs en,fa,es --out report/parity.json || exit 1; \
	python -m src.report.build_report || exit 1; \
	PORT=$$(python -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()'); \
	echo "Starting uvicorn on port $$PORT"; \
	PYTHONPATH=src uvicorn service.api:app --host 127.0.0.1 --port $$PORT --log-level warning & \
	SVCPID=$$!; \
	sleep 1; \
	curl -sf http://127.0.0.1:$$PORT/healthz > /dev/null || (kill $$SVCPID; exit 1); \
	echo "Try: curl -sf http://127.0.0.1:$$PORT/healthz"; \
	echo "Try: curl -sf -X POST http://127.0.0.1:$$PORT/score -H 'Content-Type: application/json' -d '{\"text\":\"hello\",\"category\":\"violence\",\"language\":\"en\"}'"; \
	kill $$SVCPID || true


service-http:
	@PORT=$${PORT:-8001}; \
	WORKERS=$${WORKERS:-1}; \
	TIMEOUT=$${TIMEOUT:-5}; \
	LOG_LEVEL=$${LOG_LEVEL:-warning}; \
	echo "Starting HTTP on $$PORT (workers=$$WORKERS)"; \
	PYTHONPATH=src uvicorn service.api:app --host 0.0.0.0 --port $$PORT --workers $$WORKERS --timeout-keep-alive $$TIMEOUT --log-level $$LOG_LEVEL

# Fixed REST serve per quickstart
serve-rest:
	PYTHONPATH=src uvicorn service.api:app --host 0.0.0.0 --port 8001 --workers 4

service-grpc:
	@PORT=$${GRPC_PORT:-50051}; echo "Starting gRPC on $$PORT"; PYTHONPATH=src python -m src.grpc.server

# Fixed gRPC serve per quickstart
serve-grpc:
	PYTHONPATH=$(PWD) python src/grpc_service/server.py

grpc-serve-tls:
	@CERT=$${GRPC_TLS_CERT:-certs/server.crt}; \
	KEY=$${GRPC_TLS_KEY:-certs/server.key}; \
	PORT=$${GRPC_TLS_PORT:-5443}; \
	echo "Starting gRPC TLS on $$PORT"; \
	PYTHONPATH=$(PWD) GRPC_TLS_ENABLED=true GRPC_TLS_CERT=$$CERT GRPC_TLS_KEY=$$KEY GRPC_TLS_PORT=$$PORT ./.venv/bin/python src/grpc_service/server.py

build-wheel:
	python -m build

docker:
	docker build -t safety-eval-mini:latest .

pack:
	PYTHONPATH=src python -m src.evidence.pack


grpc-gen:
	./.venv/bin/python -m grpc_tools.protoc \
	  -I src/grpc_service \
	  --python_out=src/grpc_generated \
	  --grpc_python_out=src/grpc_generated \
	  src/grpc_service/score.proto

grpc-serve:
	PYTHONPATH=$(PWD) ./.venv/bin/python src/grpc_service/server.py

grpc-client:
	PYTHONPATH=$(PWD) ./.venv/bin/python src/grpc_service/clients/py_client.py


# gRPC CLI helpers (grpcurl)
GRPC_ADDR ?= 127.0.0.1:50051
GRPC_IMPORT ?= src/grpc
GRPC_PROTO ?= $(GRPC_IMPORT)/score.proto

grpc-health:
	grpcurl -plaintext -import-path $(GRPC_IMPORT) \
	 -proto google/grpc/health/v1/health.proto \
	 -d '{}' $(GRPC_ADDR) grpc.health.v1.Health/Check

grpc-score:
	grpcurl -plaintext -import-path $(GRPC_IMPORT) -proto score.proto -d '{"text":"hello","category":"violence","language":"en","guard":"candidate"}' $(GRPC_ADDR) seval.ScoreService/Score

load-grpc:
	ghz --insecure --proto $(GRPC_PROTO) --call seval.ScoreService.Score \
	    -d '{"text":"hello","category":"violence","language":"en","guard":"candidate"}' \
	    -c 16 -n 5000 $(GRPC_ADDR)

grpc-batch:
	grpcurl -plaintext -import-path $(GRPC_IMPORT) -proto $(GRPC_PROTO) \
	  -d '{"items":[{"text":"a","category":"violence","language":"en","guard":"candidate"}]}' \
	  $(GRPC_ADDR) seval.ScoreService/BatchScore

test:
	pytest -q

fmt:
	ruff check --fix . && ruff format .

# Smart HTTP server with automatic port selection
serve:
	@python3 - <<'PY'
import socket, http.server, socketserver, os, subprocess
port = int(os.environ.get('PORT', '3001'))
s = socket.socket()
try:
    s.bind(('127.0.0.1', port))
    s.close()
    print(f"Starting HTTP server on http://127.0.0.1:{port}")
    os.execvp('python3', ['python3', '-m', 'http.server', str(port), '--directory', 'report'])
except OSError:
    print(f"❌ Port {port} in use. Try these fixes:")
    print(f"   1. Set different port: PORT=8080 make serve")
    print(f"   2. Kill process: lsof -ti :{port} | xargs kill -9")
    result = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)
    if result.stdout:
        print(f"\nProcess using port {port}:")
        print(result.stdout)
PY

# Generate gRPC stubs
stubs:
	python3 -m grpc_tools.protoc -I src/grpc_service \
		--python_out=src/grpc_generated \
		--grpc_python_out=src/grpc_generated \
		src/grpc_service/score.proto
	@echo "✅ gRPC stubs generated"

# Run gRPC server
run-grpc:
	PYTHONPATH=$(PWD)/src python3 src/grpc_service/server.py

# gRPC smoke tests
grpc-smoke:
	@echo "Testing gRPC server..."
	@grpcurl -plaintext 127.0.0.1:50051 list || echo "❌ Reflection not enabled. Use: ENABLE_GRPC_REFLECTION=true make run-grpc"
	@grpcurl -plaintext -d '{"text":"hello","category":"violence","language":"en"}' 127.0.0.1:50051 seval.ScoreService/Score || echo "❌ gRPC server not running. Run: make run-grpc"
