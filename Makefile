help:
	@echo "Makefile commands:"
	@echo "  docker-dev-run: Start the docker compose stack"
	@echo "  help: Show this help message"


.ONESHELL:
docker-dev-run:
	export $(grep -v '^#' .env | xargs -d '\n')
	docker compose up --build --watch

.ONESHELL:
docker-vllm-run:
	export $(grep -v '^#' .env | xargs -d '\n')
	docker compose -f docker-compose-vllm.yaml up
