# Pasta de saída configurável
BUILD_DIR ?= build
BUILD_TEMP := $(BUILD_DIR)/temp

# Binários das ferramentas
ESPRESSO    := ./Progs/espresso-logic/bin/espresso
GALETTE     := ./Progs/galasm/target/release/galette
XGPRO_LOGIC := ./Progs/xgpro-logic/build/xgpro-logic

# Scripts
SCRIPTS_PY := $(wildcard scripts/*.py) $(wildcard scripts/lib/*.py)

# Descoberta dinâmica de arquivos
VALID_TXT_CIRCUITS    := $(shell python3 scripts/discover_targets.py --circuits-txt)
VALID_TXT_TEMP        := $(shell python3 scripts/discover_targets.py --temp-txt $(BUILD_DIR))
VALID_TXT             := $(VALID_TXT_CIRCUITS) $(VALID_TXT_TEMP)

CIRCUITS_PY           := $(shell python3 scripts/discover_targets.py --py)
CIRCUITS_PY_WITH_JSON := $(shell python3 scripts/discover_targets.py --py-with-json)
CIRCUITS_V_WITH_JSON  := $(shell python3 scripts/discover_targets.py --verilog-with-json)

# Geração step1: .py → .txt e .json
CIRCUITS_GEN_TXT  := $(foreach py, $(CIRCUITS_PY), $(BUILD_TEMP)/$(basename $(notdir $(py))).txt)
TEMP_JSON_TARGETS := $(foreach py, $(CIRCUITS_PY_WITH_JSON), $(BUILD_TEMP)/$(basename $(notdir $(py))).json)

# .json copiados para BUILD_TEMP (necessário antes do step2)
TEMP_JSON_FROM_V  := $(foreach v, $(CIRCUITS_V_WITH_JSON), $(BUILD_TEMP)/$(basename $(notdir $(v))).json)

# Todos os stems (union de .txt e .v, sem duplicatas)
ALL_STEMS_V   := $(foreach v, $(CIRCUITS_V_WITH_JSON), $(basename $(notdir $(v))))
ALL_STEMS_TXT := $(foreach t, $(VALID_TXT), $(basename $(notdir $(t))))
ALL_STEMS     := $(sort $(ALL_STEMS_V) $(ALL_STEMS_TXT))

# Lista de .pla intermediários (só usada para declarar .INTERMEDIATE)
ALL_MIN_PLA := $(addprefix $(BUILD_TEMP)/, $(addsuffix .pla, $(ALL_STEMS)))

# Targets step2 unificados
CIRC_ALL := $(addprefix $(BUILD_DIR)/, $(addsuffix .circ, $(ALL_STEMS)))
PLD_ALL  := $(addprefix $(BUILD_DIR)/, $(addsuffix .pld,  $(ALL_STEMS)))
TOML_ALL := $(addprefix $(BUILD_DIR)/, $(addsuffix .toml, $(ALL_STEMS)))
JED_ALL  := $(addprefix $(BUILD_DIR)/, $(addsuffix .jed,  $(ALL_STEMS)))
LGC_ALL  := $(addprefix $(BUILD_DIR)/, $(addsuffix .lgc,  $(ALL_STEMS)))

# ==========================================
# CONFIGURAÇÃO DE VPATH (Busca em Subpastas)
# ==========================================
SRC_DIRS := $(sort $(dir $(CIRCUITS_PY) $(VALID_TXT_CIRCUITS) $(CIRCUITS_V_WITH_JSON)))

# Ensina o Make a procurar os arquivos nessas pastas e na temp
vpath %.py $(SRC_DIRS)
vpath %.txt $(SRC_DIRS) $(BUILD_TEMP)
vpath %.json $(SRC_DIRS) $(BUILD_TEMP)
vpath %.v $(SRC_DIRS)
vpath %.pla $(BUILD_TEMP)

# ==========================================
# ORQUESTRAÇÃO DE MULTI-STEP
# ==========================================
.PHONY: all step1 step2 non_pld compile_jed

all: step1
	@$(MAKE) step2

step1: gen_tables
step2: all_compile

# Step1: .txt gerados de .py e todos os .json copiados para BUILD_TEMP
# As .pla são intermediárias — construídas sob demanda em step2
gen_tables: $(CIRCUITS_GEN_TXT) $(TEMP_JSON_TARGETS) $(TEMP_JSON_FROM_V)

all_compile: non_pld
	-$(MAKE) compile_jed

# Targets finais: .circ, .jed e .lgc
# .pld e .toml são intermediários (gerados e deletados automaticamente)
non_pld: $(CIRC_ALL) $(LGC_ALL)
compile_jed: $(JED_ALL)

# KEEP_ALL=1 é atalho para preservar todos os intermediários
ifdef KEEP_ALL
KEEP_PLA  := 1
KEEP_PLD  := 1
KEEP_TOML := 1
endif

# Por padrão, Make apaga intermediários (regras encadeadas).
# Use KEEP_PLA=1 / KEEP_PLD=1 / KEEP_TOML=1 (ou KEEP_ALL=1) para preservar.
ifdef KEEP_PLA
.SECONDARY: $(ALL_MIN_PLA)
endif
ifdef KEEP_PLD
.SECONDARY: $(PLD_ALL)
endif
ifdef KEEP_TOML
.SECONDARY: $(TOML_ALL)
endif

# ==========================================
# REGRAS DE CRIAÇÃO DE DIRETÓRIOS
# ==========================================
$(BUILD_DIR) $(BUILD_TEMP):
	@mkdir -p $@

# ==========================================
# ETAPA 1: Geração de Intermediários
# ==========================================

# .py → BUILD_TEMP/%.txt
$(BUILD_TEMP)/%.txt: %.py | $(BUILD_TEMP)
	python3 scripts/gen_truth_table.py -i $< -o $@ -j12

# .json → BUILD_TEMP/%.json
$(BUILD_TEMP)/%.json: %.json | $(BUILD_TEMP)
	cp $< $@

# .txt → BUILD_TEMP/%.pla  (truth_table_to_pla.py + Espresso, mantém headers)
# Aplica a Circuits/**/*.txt E a BUILD_TEMP/%.txt gerado por .py (via vpath)
$(BUILD_TEMP)/%.pla: %.txt | $(BUILD_TEMP)
	python3 scripts/truth_table_to_pla.py $< --keep-header --out-pla $@

# .v → BUILD_TEMP/%.pla  (yosys + abc; sem Espresso — abc já minimiza suficientemente)
$(BUILD_TEMP)/%.pla: %.v | $(BUILD_TEMP)
	yosys -p "read_verilog $<; hierarchy -auto-top; proc; opt; techmap; opt; \
	          write_blif $(BUILD_TEMP)/$*.blif"
	yosys-abc -c "read_blif $(BUILD_TEMP)/$*.blif; collapse; write_pla $@"
	python3 -c "p='$@'; s=open(p).read().replace('\\\\',''); open(p,'w').write(s)"
	rm -f $(BUILD_TEMP)/$*.blif

# ==========================================
# ETAPA 2: Compilação Unificada (todas as fontes via BUILD_TEMP/%.pla)
# ==========================================

# .circ
$(BUILD_DIR)/%.circ: $(BUILD_TEMP)/%.pla scripts/pla_to_logisim_sop.py | $(BUILD_DIR)
	python3 scripts/pla_to_logisim_sop.py $< --circuit-name $(basename $(notdir $@)) --out-circ $@

# .pld
$(BUILD_DIR)/%.pld: $(BUILD_TEMP)/%.pla $(BUILD_TEMP)/%.json $(SCRIPTS_PY) | $(BUILD_DIR)
	python3 scripts/pla_to_pld.py $< $(BUILD_TEMP)/$*.json $@

# .toml
$(BUILD_DIR)/%.toml: $(BUILD_TEMP)/%.pla $(BUILD_TEMP)/%.json scripts/truth_table_to_toml.py | $(BUILD_DIR)
	python3 scripts/truth_table_to_toml.py $< $(BUILD_TEMP)/$*.json -o $@

# .jed
$(BUILD_DIR)/%.jed: $(BUILD_DIR)/%.pld | $(BUILD_DIR)
	$(GALETTE) -c -f -p $<

# .lgc
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
	@echo "Checking for system dependencies (gcc, cargo, go, yosys)..."
	@if ! command -v gcc > /dev/null 2>&1 || ! command -v cargo > /dev/null 2>&1 || ! command -v go > /dev/null 2>&1 || ! command -v yosys > /dev/null 2>&1; then \
		echo "Installing missing dependencies..."; \
		sudo apt-get update && sudo apt-get install -y build-essential cargo golang-go yosys; \
	else \
		echo "All dependencies (gcc, cargo, go, yosys) are already installed."; \
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