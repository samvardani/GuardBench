.PHONY: compare report sweep store demo open

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
