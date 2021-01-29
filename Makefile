build:
	dune build

install: build
	dune install

uninstall:
	dune uninstall

clean: uninstall
	dune clean

run:
	dune build @run

doc:
	dune build @doc

.PHONY: build install uninstall run doc
