.PHONY: up down clean logs ps certs

up:
	docker compose up --build

down:
	docker compose down

clean:
	docker compose down -v

logs:
	docker compose logs -f

ps:
	docker compose ps

certs:
	@powershell -ExecutionPolicy Bypass -File scripts/export-windows-root-certs.ps1

