STAGE ?= 00
CP := $(shell ls -d checkpoints/$(STAGE)-* 2>/dev/null | head -1)

.PHONY: help start gap up down incident reset status validate snapshot

help:
	@echo "Build-a-KVStore — workshop commands"
	@echo "  make start              seed kvstore/ from checkpoint 00"
	@echo "  make gap STAGE=NN       load the gapped start for a code stage (03/04/05/08)"
	@echo "  make up STAGE=NN        start this stage's processes"
	@echo "                          (stage 01: add WORKERS=1 to demo the single-thread choke)"
	@echo "  make down               stop all workshop processes"
	@echo "  make incident STAGE=NN  run this stage's red->green check"
	@echo "  make reset STAGE=NN     reset kvstore/ to a known-good checkpoint"
	@echo "  make status             show the ladder of resolved incidents"

start:
	rm -rf kvstore && cp -r checkpoints/00-* kvstore
	@echo "kvstore/ seeded from checkpoint 00"

gap:
	rm -rf kvstore && cp -r stages/$(STAGE)-* kvstore
	@echo "kvstore/ loaded with the GAPPED starting point for stage $(STAGE)"

up:
	WORKERS=$(WORKERS) bash tools/up.sh $(STAGE)

down:
	bash tools/down.sh

incident:
	python incidents/incident_$(STAGE)_*.py

reset:
	rm -rf kvstore && cp -r $(CP) kvstore
	@echo "kvstore/ reset to $(CP)"

status:
	python tools/status.py

# --- author-only ---
validate:
	bash tools/validate_ladder.sh

snapshot:
	cp -r kvstore checkpoints/$(STAGE)-snapshot
