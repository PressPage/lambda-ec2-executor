project=$(shell basename $(CURDIR))
paramiko_version="2.4.0"


# default part
.PHONY: full

full: zip upload #cleanup

build:
	rm -f python2.7-paramiko-$(paramiko_version).zip
	docker run --rm -v `pwd`:/app -d lambci/lambda:build-python2.7 bash -c "cd /app && /app/build.sh --docker --py2-only paramiko $(paramiko_version)"


zip:
	rm -f $(project).zip
	cp python2.7-paramiko-$(paramiko_version).zip $(project).zip
	zip $(project).zip ./*.py

venv:
	@rm -rf venv
	pip install virtualenv
	virtualenv venv

upload:
	aws lambda update-function-code --function-name FUNCTION_NAME --zip-file fileb://$(project).zip

cleanup:
	rm -f $(project).zip
	rm -rf venv