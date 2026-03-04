# Pipeline: Circuits/*.txt (with same-dir *.json) -> Gal/*.pld, Gal/*.jed,
#            Gal/*.toml (vetores de teste), Gal/*.lgc (Xgpro).
# Dependencies: all scripts/*.py

SCRIPTS_PY := $(wildcard scripts/*.py)

# Detecção de Sistema Operacional para rodar TUDO via WSL se estiver no Windows
ifeq ($(OS),Windows_NT)
  # Comando base para rodar no WSL preservando o diretório atual
  RUN_WSL := wsl
else
  RUN_WSL :=
endif

# Binários das ferramentas (compilados localmente no WSL)
ESPRESSO := $(RUN_WSL) ./Progs/espresso-logic/bin/espresso
GALETTE := $(RUN_WSL) ./Progs/galasm/target/release/galette
XGPRO_LOGIC := $(RUN_WSL) ./Progs/xgpro-logic/build/xgpro-logic

# Only .txt under Circuits/ that have a matching .json in the same directory
# Usamos python3 via WSL para garantir consistência no mapeamento de arquivos
VALID_TXT := $(shell $(RUN_WSL) python3 -c "import os; [print(os.path.normpath(os.path.join(r,f)).replace(os.sep,'/')) for r,d,fs in os.walk('Circuits') for f in fs if f.endswith('.txt') and os.path.isfile(os.path.join(r,f[:-4]+'.json'))]")

PLD_TARGETS := $(foreach t, $(VALID_TXT), Gal/$(basename $(notdir $(t))).pld)
JED_TARGETS := $(foreach t, $(VALID_TXT), Gal/$(basename $(notdir $(t))).jed)
TOML_TARGETS := $(foreach t, $(VALID_TXT), Gal/$(basename $(notdir $(t))).toml)
LGC_TARGETS := $(foreach t, $(VALID_TXT), Gal/$(basename $(notdir $(t))).lgc)

define RULE_PLD
Gal/$(basename $(notdir $(1))).pld: $(1) $(1:.txt=.json) $(SCRIPTS_PY)
	$(RUN_WSL) mkdir -p Gal
	$(RUN_WSL) python3 scripts/run_pipeline.py -i $$< --pld-config $(1:.txt=.json) --pld-out $$@
endef

define RULE_JED
Gal/$(basename $(notdir $(1))).jed: $(1)
	$(RUN_WSL) mkdir -p Gal
	$(GALETTE) -c -f -p $$<
endef

define RULE_TOML
Gal/$(basename $(notdir $(1))).toml: $(1) $(1:.txt=.json) scripts/truth_table_to_toml.py
	$(RUN_WSL) mkdir -p Gal
	$(RUN_WSL) python3 scripts/truth_table_to_toml.py $(1) $(1:.txt=.json) -o $$@
endef

define RULE_LGC
Gal/$(basename $(notdir $(1))).lgc: Gal/$(basename $(notdir $(1))).toml
	$(RUN_WSL) mkdir -p Gal
	$(XGPRO_LOGIC) lgc $$< $$@
endef

$(foreach t, $(VALID_TXT), $(eval $(call RULE_PLD,$t)))
$(foreach t, $(PLD_TARGETS), $(eval $(call RULE_JED,$t)))
$(foreach t, $(VALID_TXT), $(eval $(call RULE_TOML,$t)))
$(foreach t, $(VALID_TXT), $(eval $(call RULE_LGC,$t)))

all: $(PLD_TARGETS) $(JED_TARGETS) $(TOML_TARGETS) $(LGC_TARGETS)

# --- Build Progs (Executado sempre dentro do WSL) ---

install-deps:
	@echo "Checking for system dependencies in WSL (gcc, cargo, go)..."
	$(RUN_WSL) sh -c 'if ! which gcc > /dev/null 2>&1 || ! which cargo > /dev/null 2>&1 || ! which go > /dev/null 2>&1; then \
		echo "Installing missing dependencies..."; \
		sudo apt-get update && sudo apt-get install -y build-essential cargo golang-go; \
	else \
		echo "All dependencies (gcc, cargo, go) are already installed."; \
	fi'

build-progs: install-deps build-espresso build-galasm build-xgpro-logic

build-espresso:
	@echo "Building Espresso-logic in WSL..."
	$(RUN_WSL) sh -c "cd Progs/espresso-logic/espresso-src && make clean && make CFLAGS='-std=gnu89 -w'"

build-galasm:
	@echo "Building Galasm (Galette) in WSL..."
	$(RUN_WSL) sh -c "cd Progs/galasm && cargo build --release"

build-xgpro-logic:
	@echo "Building XGpro-logic in WSL..."
	$(RUN_WSL) mkdir -p Progs/xgpro-logic/build
	$(RUN_WSL) sh -c "cd Progs/xgpro-logic && go build -o build/xgpro-logic ./cmd/xgpro-logic.app"

clean-progs:
	@echo "Cleaning Progs in WSL..."
	$(RUN_WSL) sh -c "cd Progs/espresso-logic/espresso-src && make clean"
	$(RUN_WSL) rm -rf Progs/espresso-logic/bin
	$(RUN_WSL) sh -c "cd Progs/galasm && cargo clean"
	$(RUN_WSL) rm -rf Progs/xgpro-logic/build

clean-gal:
	$(RUN_WSL) rm -rf Gal/

.PHONY: all build-progs build-espresso build-galasm build-xgpro-logic install-deps clean-progs clean-gal
