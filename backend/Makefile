# Makefile — Backend Rol 1 (empaquetado AWS, P2)
#
# Reproduce la base SQLite (e3.db) y el precálculo con un solo comando, de modo
# que "la base y el precálculo corran igual en la nube del equipo" (PLAN_ROL1 §0/§6).
#
# Uso:
#   make data     # (re)genera e3.db desde los CSV + precálculo + vistas
#   make test     # corre la suite de tests
#   make clean    # borra e3.db local
#
# PYTHON se puede sobrescribir:  make data PYTHON=python3
PYTHON ?= python

.PHONY: data load views test clean

## data: pipeline completo — loader (M1) + precálculo/vistas (M1 cruce).
data: load views

## load: carga los 23 CSV públicos a SQLite (reconstruye desde cero).
load:
	$(PYTHON) -m app.loader.load --force

## views: materializa las 10.000 evaluaciones + accesos y crea las vistas de cruce.
views:
	$(PYTHON) -m app.db.build_views

## test: suite de tests del Rol 1.
test:
	$(PYTHON) -m pytest

## clean: elimina la base local (se regenera con `make data`).
clean:
	-rm -f e3.db
