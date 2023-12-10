
install:
	@pip install -r requirements.txt
	@pip install -r requirements-dev.txt

unittest:
	@cd tests && pytest ./tests --no-header

coverage:
	@cd tests && coverage run -m pytest ./ --no-header
	@mv tests/.coverage ./.coverage
	@coverage-badge -o coverage.svg -f


