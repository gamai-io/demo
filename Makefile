ARTIFACTS ?= artifacts

.PHONY: build verify fetch clean

# Regenerate index.html from the pinned crossnode-bench v1.4.0 result files.
build:
	./build.sh

# Fail if the committed index.html differs from what the artifacts produce.
verify:
	./build.sh --check

fetch:
	rm -rf $(ARTIFACTS)
	./build.sh --check

clean:
	rm -rf $(ARTIFACTS)
