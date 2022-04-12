.PHONY: build run

export GOPROXY=https://goproxy.cn,direct
export GO111MODULE=on


build:
	./build_docker.sh
	@echo "build successfully!"

run:
	./build_docker.sh
	@echo "build successfully!"
	docker-compose down
	docker-compose up -d
	docker logs -f tg
