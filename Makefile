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

# Definição dos Targets (achatados)
CIRCUITS_GEN_TXT  := $(foreach py, $(CIRCUITS_PY), $(BUILD_TEMP)/$(basename $(notdir $(py))).txt)
TEMP_JSON_TARGETS := $(foreach py, $(CIRCUITS_PY_WITH_JSON), $(BUILD_TEMP)/$(basename $(notdir $(py))).json)

# Targets para Verilog → PLA
CIRCUITS_GEN_PLA  := $(foreach v, $(CIRCUITS_V_WITH_JSON), $(BUILD_TEMP)/$(basename $(notdir $(v))).pla)
TEMP_JSON_FROM_V  := $(foreach v, $(CIRCUITS_V_WITH_JSON), $(BUILD_TEMP)/$(basename $(notdir $(v))).json)

# Targets de step2 para fontes .txt
PLD_TARGETS  := $(foreach t, $(VALID_TXT), $(BUILD_DIR)/$(basename $(notdir $(t))).pld)
JED_TARGETS  := $(foreach t, $(VALID_TXT), $(BUILD_DIR)/$(basename $(notdir $(t))).jed)
TOML_TARGETS := $(foreach t, $(VALID_TXT), $(BUILD_DIR)/$(basename $(notdir $(t))).toml)
LGC_TARGETS  := $(foreach t, $(VALID_TXT), $(BUILD_DIR)/$(basename $(notdir $(t))).lgc)
CIRC_TARGETS := $(foreach t, $(VALID_TXT), $(BUILD_DIR)/$(basename $(notdir $(t))).circ)

# Targets de step2 para fontes .pla (Verilog)
VALID_PLA_TEMP   := $(shell python3 scripts/discover_targets.py --temp-pla $(BUILD_DIR))
PLD_FROM_PLA  := $(foreach t, $(VALID_PLA_TEMP), $(BUILD_DIR)/$(basename $(notdir $(t))).pld)
JED_FROM_PLA  := $(foreach t, $(VALID_PLA_TEMP), $(BUILD_DIR)/$(basename $(notdir $(t))).jed)
TOML_FROM_PLA := $(foreach t, $(VALID_PLA_TEMP), $(BUILD_DIR)/$(basename $(notdir $(t))).toml)
LGC_FROM_PLA  := $(foreach t, $(VALID_PLA_TEMP), $(BUILD_DIR)/$(basename $(notdir $(t))).lgc)
CIRC_FROM_PLA := $(foreach t, $(VALID_PLA_TEMP), $(BUILD_DIR)/$(basename $(notdir $(t))).circ)

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
.PHONY: all step1 step2

all: step1
	@$(MAKE) step2

step1: gen_tables
step2: all_compile

gen_tables: $(CIRCUITS_GEN_TXT) $(TEMP_JSON_TARGETS) $(CIRCUITS_GEN_PLA) $(TEMP_JSON_FROM_V)
all_compile: $(PLD_TARGETS) $(JED_TARGETS) $(TOML_TARGETS) $(LGC_TARGETS) $(CIRC_TARGETS) \
             $(PLD_FROM_PLA) $(JED_FROM_PLA) $(TOML_FROM_PLA) $(LGC_FROM_PLA) $(CIRC_FROM_PLA)

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

# Verilog → PLA completo (via BLIF para preservar nomes das portas), depois Espresso
$(BUILD_TEMP)/%.pla: %.v | $(BUILD_TEMP)
	yosys -p "read_verilog $<; hierarchy -auto-top; proc; opt; techmap; opt; \
	          write_blif $(BUILD_TEMP)/$*.blif"
	yosys-abc -c "read_blif $(BUILD_TEMP)/$*.blif; collapse; write_pla $(BUILD_TEMP)/$*_full.pla"
	python3 -c "p='$(BUILD_TEMP)/$*_full.pla'; s=open(p).read().replace('\\\\',''); open(p,'w').write(s)"
	$(ESPRESSO) $(BUILD_TEMP)/$*_full.pla > $@
	rm -f $(BUILD_TEMP)/$*.blif

# ==========================================
# ETAPA 2: Compilação (Unificada)
# ==========================================
$(BUILD_DIR)/%.pld: %.txt %.json $(SCRIPTS_PY) | $(BUILD_DIR)
	python3 scripts/run_pipeline.py -i $< --pld-config $(filter %.json,$^) --pld-out $(BUILD_DIR)/$*.pld

$(BUILD_DIR)/%.toml: %.txt %.json scripts/truth_table_to_toml.py | $(BUILD_DIR)
	python3 scripts/truth_table_to_toml.py $< $(filter %.json,$^) -o $@

$(BUILD_DIR)/%.circ: %.txt scripts/truth_table_to_pla.py scripts/pla_to_logisim_sop.py | $(BUILD_DIR)
	python3 scripts/truth_table_to_pla.py $< --keep-header \
	  | python3 scripts/pla_to_logisim_sop.py - --circuit-name $(basename $(notdir $@)) --out-circ $@

$(BUILD_DIR)/%.jed: $(BUILD_DIR)/%.pld | $(BUILD_DIR)
	$(GALETTE) -c -f -p $<

$(BUILD_DIR)/%.lgc: $(BUILD_DIR)/%.toml | $(BUILD_DIR)
	$(XGPRO_LOGIC) lgc $< $@

# ==========================================
# ETAPA 2: Compilação a partir de PLA (Verilog)
# ==========================================

# PLD de PLA minimizado (run_pipeline.py com --pla-input)
$(BUILD_DIR)/%.pld: %.pla %.json $(SCRIPTS_PY) | $(BUILD_DIR)
	python3 scripts/run_pipeline.py --pla-input -i $< --pld-config $(filter %.json,$^) --pld-out $@

# CIRC de PLA minimizado (pla_to_logisim_sop.py aceita PLA com cabeçalhos)
$(BUILD_DIR)/%.circ: %.pla scripts/pla_to_logisim_sop.py | $(BUILD_DIR)
	python3 scripts/pla_to_logisim_sop.py $< --circuit-name $(basename $(notdir $@)) --out-circ $@

# TOML do PLA completo (_full.pla – tabela verdade enumerada)
$(BUILD_DIR)/%.toml: %_full.pla %.json scripts/truth_table_to_toml.py | $(BUILD_DIR)
	python3 scripts/truth_table_to_toml.py $< $(filter %.json,$^) -o $@

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