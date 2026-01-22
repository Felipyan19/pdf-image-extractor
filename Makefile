.PHONY: help build up down restart logs clean test

help:
	@echo "PDF Image Extractor - Available commands:"
	@echo ""
	@echo "  make build    - Build Docker images"
	@echo "  make up       - Start services"
	@echo "  make down     - Stop services"
	@echo "  make restart  - Restart services"
	@echo "  make logs     - View logs"
	@echo "  make clean    - Clean up containers, images, and volumes"
	@echo "  make test     - Run tests"
	@echo ""

build:
	docker-compose build

up:
	docker-compose up -d
	@echo ""
	@echo "✅ Services started!"
	@echo "📚 API Documentation: http://localhost:5050/docs"
	@echo "🏥 Health Check: http://localhost:5050/api/v1/health"

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleaned up!"

test:
	python example_client.py
