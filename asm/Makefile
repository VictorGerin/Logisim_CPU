# customasm: tenta com ou sem .exe (funciona em Linux e Windows sem if OS)
CUSTOMASM := $(or $(shell command -v customasm 2>/dev/null),$(shell command -v customasm.exe 2>/dev/null),customasm)

install-deps:
	@echo "Checking for customasm..."
	@sh -c 'if command -v $(CUSTOMASM) > /dev/null 2>&1; then \
		echo "customasm is already installed."; \
	else \
		echo "customasm not found. Installing cargo and customasm..."; \
		if ! command -v cargo > /dev/null 2>&1; then \
			echo "Installing cargo..."; \
			sudo apt-get update && sudo apt-get install -y build-essential cargo; \
		fi; \
		cargo install customasm; \
	fi'

all: main.asm
	$(CUSTOMASM) main.asm -o main.bin
	@echo "Done"

logisim: main.asm
	$(CUSTOMASM) main.asm -o main.bin -f logisim8
	@echo "Done"

.PHONY: all logisim install-deps
