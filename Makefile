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
LFLAGS=-lflags -locamlopencv

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
#	ocamlbuild $(FLAGS) $(LFLAGS) $(NATIVE_LIB) $(BYTE_LIB)
	ocamlbuild $(FLAGS) $(NATIVE_LIB) $(BYTE_LIB)

#$(BUILT_LIBS): $(BUILD)/$(SHARED_LIB) $(MLS:=.ml) $(MLS:=.mli)
#	@echo "Building opencv OCaml library"
#	ocamlbuild $(FLAGS) $(GEN)/opencv.cmx $(GEN)/opencv.cmo $(GEN)/opencv.cmi
#	ocamlfind ocamlmklib $(BUILD)/$(GEN)/*.cmx $(BUILD)/$(GEN)/*.cmo $(BUILD)/$(GEN)/*.ml \
#		-package ctypes -package ctypes.foreign -locamlopencv -o $(BUILD)/opencv

$(INSTALLED_SHARED_LIB): $(BUILD)/$(SHARED_LIB)
	@echo "Installing shared library"
	sudo rm -f $(INSTALLED_SHARED_LIB)
	sudo cp $(BUILD)/$(SHARED_LIB) $(INSTALLED_SHARED_LIB)
#	@(which ldconfig > /dev/null && sudo ldconfig $(SHARED_LIBS_INSTALL_DIR)) || true

libinstall: $(BUILT_LIBS)
	@echo "Installing ocamlfind library"
	ocamlfind remove $(LIB_NAME)
	ocamlfind install $(LIB_NAME) $(LIB_FILES) # -dll $(BUILD)/$(SHARED_LIB)

sharedlib: $(BUILD)/$(SHARED_LIB)
lib: $(BUILT_LIBS)
install: $(INSTALLED_SHARED_LIB) libinstall

docs: $(BUILT_LIBS)
	ocamlbuild $(FLAGS) -docflags -stars opencv.docdir/index.html

$(TESTS):
	@echo "Running test: $@"
	$(MAKE) -C $@ test

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

.PHONY: default sharedlib lib libinstall install docs test clean $(TESTS) $(TESTS_CLEAN)
