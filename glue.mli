
open Ctypes

val list_of_vector : 'a typ -> unit ptr -> 'a list
val vector_of_list : 'a typ -> 'a list -> unit ptr
