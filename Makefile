BUILD=_build

GEN=gen
GENERATOR=generator.py
GENERATOR_SRC=$(GENERATOR) hdr_parser.py type_manager.py incl/*

CPP=$(GEN)/opencv.cpp glue.cpp
HEADERS=$(GEN)/opencv.h glue.h
SHARED_LIB=libocamlopencv.so
SHARED_LIBS_INSTALL_DIR=/usr/lib/
INSTALLED_SHARED_LIB=$(SHARED_LIBS_INSTALL_DIR)/$(SHARED_LIB)

MLS=$(GEN)/opencv
FLAGS=-use-ocamlfind

LIB_NAME=opencv
LIB_FILES=META $(BUILD)/$(GEN)/opencv.cmxa $(BUILD)/$(GEN)/*.cmx \
	$(BUILD)/$(GEN)/*.cmi $(BUILD)/$(GEN)/*.a $(BUILD)/$(GEN)/*.cma
NATIVE_LIB=$(GEN)/opencv.cmxa
BYTE_LIB=$(GEN)/opencv.cma
BUILT_LIBS=$(BUILD)/$(NATIVE_LIB) $(BUILD)/$(BYTE_LIB)

TESTS=$(wildcard tests/*)
TESTS_CLEAN=$(TESTS:=.clean)

default: install

$(GEN)/%: ${GENERATOR_SRC}
	@echo "Running generator script"
	mkdir -p $(GEN)
	./$(GENERATOR) $(GEN)

$(BUILD)/$(SHARED_LIB): $(CPP) $(HEADERS)
	@echo "Compiling shared library"
	mkdir -p $(BUILD)
	g++ --shared -fPIC -g -std=c++11 -pedantic -Werror -Wall $(CPP) \
		-I `ocamlc -where` `pkg-config --libs --cflags opencv4` \
		-o $(BUILD)/$(SHARED_LIB)
	chmod 755 $(BUILD)/$(SHARED_LIB)

$(BUILT_LIBS): $(BUILD)/$(SHARED_LIB) $(MLS:=.ml) $(MLS:=.mli)
	@echo "Building opencv OCaml library"
	ocamlbuild $(FLAGS) $(NATIVE_LIB) $(BYTE_LIB)

$(INSTALLED_SHARED_LIB): $(BUILD)/$(SHARED_LIB)
	@echo "Installing shared library"
#	needing sudo is unfortunate but we need to put the shared library
#	somewhere that the linker will find it
	sudo rm -f $(INSTALLED_SHARED_LIB)
	sudo cp $(BUILD)/$(SHARED_LIB) $(INSTALLED_SHARED_LIB)

libinstall: $(BUILT_LIBS)
	@echo "Installing ocamlfind library"
	ocamlfind remove $(LIB_NAME)
	ocamlfind install $(LIB_NAME) $(LIB_FILES)

sharedlib: $(BUILD)/$(SHARED_LIB)
lib: $(BUILT_LIBS)
install: $(INSTALLED_SHARED_LIB) libinstall

docs: $(BUILT_LIBS)
	ocamlbuild $(FLAGS) -docflags -stars opencv.docdir/index.html

$(TESTS):
	@echo "Running test: $@"
#	clean first to guarantee that we pick up changes to the library
	$(MAKE) -C $@ clean test

test: $(INSTALLED_SHARED_LIB) libinstall $(TESTS)

$(TESTS_CLEAN):
#	this is a stupid hack
	$(MAKE) -C $(basename $@) clean

clean: $(TESTS_CLEAN)
	ocamlbuild -clean
	rm -f $(BUILD)/$(SHARED_LIB)
	rm -rf $(GEN)
	sudo rm -f $(INSTALLED_SHARED_LIB)
	ocamlfind remove $(LIB_NAME)

.PHONY: default sharedlib lib libinstall install docs test clean \
	$(TESTS) $(TESTS_CLEAN)
