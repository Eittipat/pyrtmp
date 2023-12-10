
install:
	@pip install -r requirements.txt
	@pip install -r requirements-dev.txt

unittest:
	@cd tests && pytest ./ --no-header



