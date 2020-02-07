
open Ctypes
open Foreign

let __vector_data = foreign "vector_data" (ptr void @-> returning (ptr void))
let __vector_length = foreign "vector_length" (ptr void @-> returning int)
let __create_vector =
  foreign "create_vector" (ptr void @-> int @-> int @-> returning (ptr void))

(* let list_of_vector (p : unit ptr) (size : int) =
 *   let len = __vector_length p in
 *   let start = __vector_data p in
 *   let rec builder (pos : unit ptr) acc =
 *     if ptr_diff pos start < 0 then acc
 *     else builder (pos -@ size) (Root.get pos) in
 *   builder (start +@ ((len - 1) * size)) [] *)

let list_of_vector (t : 'a typ) (p : unit ptr) =
  let len = __vector_length p in
  let start = __vector_data p in
  CArray.from_ptr (from_voidp t start) (len / (sizeof t)) |> CArray.to_list

let vector_of_list (t : 'a typ) (lst : 'a list) =
  let arr = CArray.of_list t lst in
  __create_vector (CArray.start arr |> to_voidp) (CArray.length arr) (sizeof t)
