
.PHONY: up down restart logs eval shell

up:
	cd infra/docker && docker compose up -d

down:
	cd infra/docker && docker compose down

restart:
	cd infra/docker && docker compose restart

logs:
	cd infra/docker && docker compose logs -f

shell:
	docker exec -it pandora-cortex /bin/bash

# ==========================================
# Evaluation Pipeline
# ==========================================
eval:
	@echo "🧪 Running Evaluation Suite (Containerized)..."
	# 1. Install Eval Dependencies inside container (temporary)
	docker exec pandora-cortex pip install deepeval requests
	
	# 2. Run DeepEval Quality Gate
	@echo "🚀 Running DeepEval RAG Triad Metrics..."
	docker exec pandora-cortex python3 tests/evaluation/run_evals.py

eval-local:
	@echo "🧪 Running Evaluation Suite (Local)..."
	cd cortex && python ../tests/evaluation/run_evals.py

