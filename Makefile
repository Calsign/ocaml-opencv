build:
	dune build

install:
	dune install

uninstall:
	dune uninstall

run:
	dune build @run

doc:
	dune build @doc

.PHONY: build install uninstall run doc
