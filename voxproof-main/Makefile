.PHONY: install test backend frontend run report demo clean

install:
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

test:
	cd backend && python3 -m pytest tests/ -v

backend:
	cd backend && python3 -m uvicorn app.main:app --port 8765 --reload

frontend:
	cd frontend && npm run dev

run: backend frontend

cli-run:
	cd backend && python3 -m app.cli run finance_voice_agent

report:
	curl -s -X POST http://localhost:8765/api/run/finance_voice_agent > /dev/null
	curl -s http://localhost:8765/api/runs/1/report > voxproof_report.html
	@echo "Report saved to voxproof_report.html"

demo:
	@echo "=== VOXPROOF DEMO ==="
	@echo "1. Backend: http://localhost:8765"
	@echo "2. Frontend: http://localhost:5173"
	@echo "3. CLI:    make cli-run"
	@echo "4. Report: make report"

clean:
	rm -f voxproof.db voxproof_report_*.html
	rm -rf frontend/dist/
