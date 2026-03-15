# Pasta de saída configurável
BUILD_DIR ?= build
BUILD_TEMP := $(BUILD_DIR)/temp

# Binários das ferramentas
ESPRESSO    := ./Progs/espresso-logic/bin/espresso
GALETTE     := ./Progs/galasm/target/release/galette
XGPRO_LOGIC := ./Progs/xgpro-logic/build/xgpro-logic

# Scripts
SCRIPTS_PY := $(wildcard scripts/*.py)

# Descoberta dinâmica de arquivos
VALID_TXT_CIRCUITS    := $(shell python3 scripts/discover_targets.py --circuits-txt)
VALID_TXT_TEMP        := $(shell python3 scripts/discover_targets.py --temp-txt $(BUILD_DIR))
VALID_TXT             := $(VALID_TXT_CIRCUITS) $(VALID_TXT_TEMP)

CIRCUITS_PY           := $(shell python3 scripts/discover_targets.py --py)
CIRCUITS_PY_WITH_JSON := $(shell python3 scripts/discover_targets.py --py-with-json)

# Definição dos Targets (achatados)
CIRCUITS_GEN_TXT  := $(foreach py, $(CIRCUITS_PY), $(BUILD_TEMP)/$(basename $(notdir $(py))).txt)
TEMP_JSON_TARGETS := $(foreach py, $(CIRCUITS_PY_WITH_JSON), $(BUILD_TEMP)/$(basename $(notdir $(py))).json)

PLD_TARGETS  := $(foreach t, $(VALID_TXT), $(BUILD_DIR)/$(basename $(notdir $(t))).pld)
JED_TARGETS  := $(foreach t, $(VALID_TXT), $(BUILD_DIR)/$(basename $(notdir $(t))).jed)
TOML_TARGETS := $(foreach t, $(VALID_TXT), $(BUILD_DIR)/$(basename $(notdir $(t))).toml)
LGC_TARGETS  := $(foreach t, $(VALID_TXT), $(BUILD_DIR)/$(basename $(notdir $(t))).lgc)
PLA_TARGETS  := $(foreach t, $(VALID_TXT), $(BUILD_DIR)/$(basename $(notdir $(t))).txt)
CIRC_TARGETS := $(foreach t, $(VALID_TXT), $(BUILD_DIR)/$(basename $(notdir $(t))).circ)

# ==========================================
# CONFIGURAÇÃO DE VPATH (Busca em Subpastas)
# ==========================================
SRC_DIRS := $(sort $(dir $(CIRCUITS_PY) $(VALID_TXT_CIRCUITS)))

# Ensina o Make a procurar os arquivos nessas pastas e na temp
vpath %.py $(SRC_DIRS)
vpath %.txt $(SRC_DIRS) $(BUILD_TEMP)
vpath %.json $(SRC_DIRS) $(BUILD_TEMP)

# ==========================================
# ORQUESTRAÇÃO DE MULTI-STEP
# ==========================================
.PHONY: all step1 step2

all: step1
	@$(MAKE) step2

step1: gen_tables
step2: all_compile

gen_tables: $(CIRCUITS_GEN_TXT) $(TEMP_JSON_TARGETS)
all_compile: $(PLD_TARGETS) $(JED_TARGETS) $(TOML_TARGETS) $(LGC_TARGETS) $(PLA_TARGETS) $(CIRC_TARGETS)

# ==========================================
# REGRAS DE CRIAÇÃO DE DIRETÓRIOS
# ==========================================
$(BUILD_DIR) $(BUILD_TEMP):
	@mkdir -p $@

# ==========================================
# ETAPA 1: Geração de Tabelas
# ==========================================
$(BUILD_TEMP)/%.txt: %.py | $(BUILD_TEMP)
	python3 scripts/gen_truth_table.py -i $< -o $@ -j12

$(BUILD_TEMP)/%.json: %.json | $(BUILD_TEMP)
	cp $< $@

# ==========================================
# ETAPA 2: Compilação (Unificada)
# ==========================================
$(BUILD_DIR)/%.pld $(BUILD_DIR)/%_plarom.xml: %.txt %.json $(SCRIPTS_PY) | $(BUILD_DIR)
	python3 scripts/run_pipeline.py -i $< --pld-config $(filter %.json,$^) --pld-out $(BUILD_DIR)/$*.pld --pla-rom-out $(BUILD_DIR)/$*_plarom.xml

$(BUILD_DIR)/%.toml: %.txt %.json scripts/truth_table_to_toml.py | $(BUILD_DIR)
	python3 scripts/truth_table_to_toml.py $< $(filter %.json,$^) -o $@

$(BUILD_DIR)/%.txt: %.txt scripts/truth_table_to_pla.py | $(BUILD_DIR)
	python3 scripts/truth_table_to_pla.py $< --use-x --out-pla $@

$(BUILD_DIR)/%.circ: %.txt scripts/truth_table_to_pla.py scripts/pla_to_logisim_sop.py | $(BUILD_DIR)
	python3 scripts/truth_table_to_pla.py $< --keep-header \
	  | python3 scripts/pla_to_logisim_sop.py - --circuit-name $(basename $(notdir $@)) --out-circ $@

$(BUILD_DIR)/%.jed: $(BUILD_DIR)/%.pld | $(BUILD_DIR)
	$(GALETTE) -c -f -p $<

$(BUILD_DIR)/%.lgc: $(BUILD_DIR)/%.toml | $(BUILD_DIR)
	$(XGPRO_LOGIC) lgc $< $@
# ==========================================
# ASSEMBLY E LOGISIM (Delegação para asm/)
# ==========================================
asm:
	$(MAKE) -C asm all

logisim:
	$(MAKE) -C asm logisim
	
# ==========================================
# REGRAS DOS PROGRAMAS DEPENDENTES
# ==========================================
install-deps:
	@echo "Checking for system dependencies (gcc, cargo, go)..."
	@if ! command -v gcc > /dev/null 2>&1 || ! command -v cargo > /dev/null 2>&1 || ! command -v go > /dev/null 2>&1; then \
		echo "Installing missing dependencies..."; \
		sudo apt-get update && sudo apt-get install -y build-essential cargo golang-go; \
	else \
		echo "All dependencies (gcc, cargo, go) are already installed."; \
	fi
	$(MAKE) -C asm install-deps

build-progs: install-deps build-espresso build-galasm build-xgpro-logic

build-espresso:
	@echo "Building Espresso-logic..."
	cd Progs/espresso-logic/espresso-src && $(MAKE) clean && $(MAKE) CFLAGS='-std=gnu89 -w'

build-galasm:
	@echo "Building Galasm (Galette)..."
	cd Progs/galasm && cargo build --release

build-xgpro-logic:
	@echo "Building XGpro-logic..."
	mkdir -p Progs/xgpro-logic/build
	cd Progs/xgpro-logic && go build -o build/xgpro-logic ./cmd/xgpro-logic.app

clean-progs:
	@echo "Cleaning Progs..."
	cd Progs/espresso-logic/espresso-src && $(MAKE) clean
	rm -rf Progs/espresso-logic/bin
	cd Progs/galasm && cargo clean
	rm -rf Progs/xg