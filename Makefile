.PHONY: compare report sweep store demo open runtime-demo service

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
