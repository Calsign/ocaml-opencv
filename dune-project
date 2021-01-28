(lang dune 2.7)
(name opencv)

(generate_opam_files true)

(source (github Calsign/ocaml-opencv))
;(license ISC)
(authors "William Smith")
(maintainers "William Smith")

(package
 (name opencv)
 (synopsis "OCaml bindings for OpenCV")
 (depends
  ctypes-foregin
  (dune (>= 2.7))
  owl))
