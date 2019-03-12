all: dev

dev: 
	pip install -r requirements-dev.txt
	pip install -e .

freeze: 
	pip freeze | sort | grep -v 'simpy-events'
test: 
	cd tests && ( pytest -rXxs -vv --cov-report html --cov-report term-missing --cov simpy-events )

doc: 
	cd docs && make html

find-version:
	egrep --recursive "(version|__version__|release) ?= ?['\"]\d+\.\d+\.\d+['\"]" .
