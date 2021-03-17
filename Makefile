all:
	python -m src 

export_TV:
	python -m src db_export -d 1 -f tvkill

tests:
	pytest tests/

.PHONY: tests
