
OUT=demo_reuse.native

default:
	ocamlbuild -use-ocamlfind -pkgs opencv,owl $(OUT)

run: default
	./$(OUT)

clean:
	ocamlbuild -clean

test: run

.PHONY: default run clean test
