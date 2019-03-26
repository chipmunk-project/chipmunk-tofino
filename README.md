# Chipmunk

## Installation
- Install [antlr](https://www.antlr.org/)
- `pip3 install chipc` or in this directory `pip3 install .`

## How to

### Generate Parser

`antlr chipc/stateful_alu.g4 -Dlanguage=Python3 -visitor -package chipc`

### Codegen

```shell
python3 chipmunk.py example_specs/simple.sk example_alus/raw.stateful_alu 2 2 codegen sample1 serial
```

### Optimization Verification

```shell
python3 chipmunk.py example_specs/simple.sk example_alus/raw.stateful_alu 1 1 optverify sample1 serial
python3 chipmunk.py example_specs/simple.sk example_alus/raw.stateful_alu 1 1 optverify sample2 serial
python3 optverify.py sample1 sample2 example_transforms/very_simple.transform
```

### Test

Simply run `nosetests`, after installing
[nose](https://nose.readthedocs.io/en/latest/).

Can also run: `python3 -m unittest`

If you want to add a test, add a new file in [tests](tests/) directory or add
test cases in existing `test_*.py` file.
