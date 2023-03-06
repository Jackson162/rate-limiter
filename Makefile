redis:
	docker compose -f ./docker-compose.dev.yaml up --force-recreate

dev:
	uvicorn main:app --reload
