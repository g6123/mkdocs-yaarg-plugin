test:
	python -m pytest -s

publish:
	python -m build
	python -m twine upload dist/*

clean:
	rm -rf build/ dist/ *.egg-info
