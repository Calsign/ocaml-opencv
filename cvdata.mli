open Ctypes

type t =
  | Mat of Mat.t
  | Unknown of unit ptr

val of_mat : Mat.t -> t
val to_mat : t -> Mat.t

val clone : t -> t

val pack_cvdata: t -> unit ptr
val pack_cvdata_post: t -> unit ptr -> unit
val extract_cvdata: unit ptr -> t
val pack_cvdata_array: t list -> unit ptr
val pack_cvdata_array_post: t list ref -> unit ptr -> unit
