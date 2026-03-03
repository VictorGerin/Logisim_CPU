# Pipeline: Circuits/*.txt (with same-dir *.json) -> Gal/*.pld
# Dependencies: all scripts/*.py

SCRIPTS_PY := $(wildcard scripts/*.py)

# Only .txt under Circuits/ that have a matching .json in the same directory
# (Python used so this works on Windows where shell find is not Unix find)
VALID_TXT := $(shell python -c "import os; [print(os.path.normpath(os.path.join(r,f)).replace(os.sep,'/')) for r,d,fs in os.walk('Circuits') for f in fs if f.endswith('.txt') and os.path.isfile(os.path.join(r,f[:-4]+'.json'))]")

PLD_TARGETS := $(foreach t, $(VALID_TXT), Gal/$(basename $(notdir $(t))).pld)

define RULE_PLD
Gal/$(basename $(notdir $(1))).pld: $(1) $(1:.txt=.json) $(SCRIPTS_PY)
	mkdir -p Gal
	python3 scripts/run_pipeline.py -i $$< --pld-config $(1:.txt=.json) --pld-out $$@
endef

$(foreach t, $(VALID_TXT), $(eval $(call RULE_PLD,$t)))

all: $(PLD_TARGETS)

.PHONY: all
