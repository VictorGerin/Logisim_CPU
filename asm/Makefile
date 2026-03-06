.SILENT:

# Detecção de Sistema Operacional para rodar via WSL no Windows
ifeq ($(OS),Windows_NT)
  RUN_WSL := wsl
  CUSTOMASM := customasm.exe
else
  RUN_WSL :=
  CUSTOMASM := customasm
endif

install-deps:
	@echo "Checking for customasm..."
	$(RUN_WSL) sh -c 'if which $(CUSTOMASM) > /dev/null 2>&1; then \
		echo "customasm is already installed."; \
	else \
		echo "customasm not found. Installing cargo and customasm..."; \
		if ! which cargo > /dev/null 2>&1; then \
			echo "Installing cargo..."; \
			sudo apt-get update && sudo apt-get install -y build-essential cargo; \
		fi; \
		cargo install customasm; \
	fi'

all: main.asm
	$(RUN_WSL) $(CUSTOMASM) main.asm -o main.bin
	@echo "Done"

logisim: main.asm
	$(RUN_WSL) $(CUSTOMASM) main.asm -o main.bin -f logisim8
	@echo "Done"

.PHONY: all logisim install-deps
