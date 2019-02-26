Installation
- Install [antlr](https://www.antlr.org/)
- `pip3 install antlr4-python3-runtime`
- `pip3 install overrides` or `pip3 install --user overrides`
- Generate ALU parser: `antlr4 -Dlanguage=Python3 -visitor stateful_alu.g4`

Example of code generation:

```shell
python3 chipmunk.py example_specs/simple.sk example_alus/raw.stateful_alu 2 2 codegen sample1
```

Example of optimization verification:

```shell
python3 chipmunk.py example_specs/simple.sk example_alus/raw.stateful_alu 1 1 optverify sample1
python3 chipmunk.py example_specs/simple.sk example_alus/raw.stateful_alu 1 1 optverify sample2
python3 optverify.py sample1 sample2 example_transforms/very_simple.transform
```
