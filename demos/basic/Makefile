
OUT=basic.native

default:
	ocamlbuild -use-ocamlfind -pkgs opencv,owl $(OUT)

run: default
	./$(OUT)

clean:
	ocamlbuild -clean

.PHONY: default run clean
