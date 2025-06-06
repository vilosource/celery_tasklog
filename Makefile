.PHONY: docker-build docker-up docker-down docker-clean package-build package-clean

# Docker helpers
docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-clean:
	docker compose down -v

# Build the celery_tasklog package
package-build:
	cd celery_tasklog && poetry build

package-clean:
	rm -rf celery_tasklog/dist
