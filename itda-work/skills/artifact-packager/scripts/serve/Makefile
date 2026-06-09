PLATFORMS := darwin/amd64 darwin/arm64 linux/amd64 linux/arm64 windows/amd64

.PHONY: embed dir all build-embed build-dir clean

embed: build-embed

dir: build-dir

all: build-embed build-dir

build-embed:
	@mkdir -p build/embed
	@for target in $(PLATFORMS); do \
		goos=$${target%/*}; \
		goarch=$${target#*/}; \
		ext=""; \
		if [ "$$goos" = "windows" ]; then ext=".exe"; fi; \
		out="build/embed/serve-$${goos}-$${goarch}$$ext"; \
		echo "CGO_ENABLED=0 GOOS=$$goos GOARCH=$$goarch go build -tags embed -o $$out ."; \
		CGO_ENABLED=0 GOOS=$$goos GOARCH=$$goarch go build -tags embed -o "$$out" .; \
	done

build-dir:
	@mkdir -p build/dir
	@for target in $(PLATFORMS); do \
		goos=$${target%/*}; \
		goarch=$${target#*/}; \
		ext=""; \
		if [ "$$goos" = "windows" ]; then ext=".exe"; fi; \
		out="build/dir/serve-$${goos}-$${goarch}$$ext"; \
		echo "CGO_ENABLED=0 GOOS=$$goos GOARCH=$$goarch go build -o $$out ."; \
		CGO_ENABLED=0 GOOS=$$goos GOARCH=$$goarch go build -o "$$out" .; \
	done

clean:
	rm -rf build
