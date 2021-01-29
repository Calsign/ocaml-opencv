open Ctypes

type t = { w : float; x : float; y : float; z : float }

val color1 : float -> t
val color2 : float -> float -> t
val color3 : float -> float -> float -> t
val color4 : float -> float -> float -> float -> t
val ctypes_to_ocaml: unit ptr -> t
val ocaml_to_ctypes: t -> unit ptr
