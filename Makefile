.PHONY: docker-build docker-up docker-down docker-clean package-build package-clean package-publish

# Docker helpers (using development compose file)
docker-build:
	docker compose -f docker-compose.dev.yml build

docker-up:
	docker compose -f docker-compose.dev.yml up -d

docker-down:
	docker compose -f docker-compose.dev.yml down

docker-clean:
	docker compose -f docker-compose.dev.yml down -v

# Package management targets
package-build:
	cd celery_tasklog && poetry build

package-clean:
	rm -rf celery_tasklog/dist

# Publish the package to PyPI
package-publish:
	cd celery_tasklog && poetry publish

# Combined build and publish
package-release: package-clean package-build package-publish
