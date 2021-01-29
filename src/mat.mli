open Bigarray
open Ctypes_static

type cmat = unit ptr

type t = (int, int8_unsigned_elt, c_layout) Genarray.t

(** [create ()] is a fresh mat. *)
val create : unit -> t

(** [clone src] is a fresh mat containing the same data as
    [src], but with a different underlying array so that the
    new mat is independent from [src]. *)
val clone : t -> t

val cmat_of_bigarray: t -> cmat
val bigarray_of_cmat: cmat -> t
val copy_cmat_bigarray: cmat -> t -> unit
