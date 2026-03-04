# Pipeline: Circuits/*.txt (with same-dir *.json) -> Gal/*.pld, Gal/*.jed,
#            Gal/*.toml (vetores de teste), Gal/*.lgc (Xgpro).
# Dependencies: all scripts/*.py

SCRIPTS_PY := $(wildcard scripts/*.py)
XGPRO_LOGIC := Progs/xgpro-logic/build/xgpro-logic.exe

# Only .txt under Circuits/ that have a matching .json in the same directory
# (Python used so this works on Windows where shell find is not Unix find)
VALID_TXT := $(shell python scripts/get_valid_txt.py)

PLD_TARGETS := $(foreach t, $(VALID_TXT), Gal/$(basename $(notdir $(t))).pld)
JED_TARGETS := $(foreach t, $(VALID_TXT), Gal/$(basename $(notdir $(t))).jed)
TOML_TARGETS := $(foreach t, $(VALID_TXT), Gal/$(basename $(notdir $(t))).toml)
LGC_TARGETS := $(foreach t, $(VALID_TXT), Gal/$(basename $(notdir $(t))).lgc)

define RULE_PLD
Gal/$(basename $(notdir $(1))).pld Gal/$(basename $(notdir $(1)))_plarom.xml: $(1) $(1:.txt=.json) $(SCRIPTS_PY)
	mkdir -p Gal
	python3 scripts/run_pipeline.py -i $$< --pld-config $(1:.txt=.json) --pld-out Gal/$(basename $(notdir $(1))).pld --pla-rom-out Gal/$(basename $(notdir $(1)))_plarom.xml > /dev/null
endef

define RULE_JED
Gal/$(basename $(notdir $(1))).jed: $(1)
	mkdir -p Gal
	galette.exe -c -f -p  $$<
endef

define RULE_TOML
Gal/$(basename $(notdir $(1))).toml: $(1) $(1:.txt=.json) scripts/truth_table_to_toml.py
	mkdir -p Gal
	python3 scripts/truth_table_to_toml.py $(1) $(1:.txt=.json) -o $$@
endef

define RULE_LGC
Gal/$(basename $(notdir $(1))).lgc: Gal/$(basename $(notdir $(1))).toml $(XGPRO_LOGIC)
	$(XGPRO_LOGIC) lgc $$< $$@
endef

$(foreach t, $(VALID_TXT), $(eval $(call RULE_PLD,$t)))
$(foreach t, $(PLD_TARGETS), $(eval $(call RULE_JED,$t)))
$(foreach t, $(VALID_TXT), $(eval $(call RULE_TOML,$t)))
$(foreach t, $(VALID_TXT), $(eval $(call RULE_LGC,$t)))

all: $(PLD_TARGETS) $(JED_TARGETS) $(TOML_TARGETS) $(LGC_TARGETS)

.PHONY: all
