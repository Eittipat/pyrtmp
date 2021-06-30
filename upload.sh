!#/bin/bash
set -euo pipefail

rm -rf dist
rm -rf pyrtmp.egg-info
python setup.py sdist
twine upload dist/*
