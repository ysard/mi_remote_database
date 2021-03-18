all:
	python -m src 

export_TV:
	python -m src db_export -d 1 -f tvkill

tests:
	pytest tests/

compress_db:
	XZ_OPT=-9 tar Jcvf database_dump.tar.xz ./database_dump/
	@#tar -I "pxz -9" -cvf database_dump.tar.xz ./database_dump/

decompress_db:
	tar Jxvf database_dump.tar.xz

.PHONY: tests
