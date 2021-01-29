open Bigarray
open Ctypes
open Ctypes_static

let foreign = Loader.foreign

type t = (int, int8_unsigned_elt, c_layout) Genarray.t

type cmat = unit ptr
let voidp = ptr void

let __mat_of_bigarray =
  foreign "mat_of_bigarray" (int @-> ptr int @-> ptr int @-> returning voidp)

let cmat_of_bigarray (m : t) : cmat =
  let num_dims = Genarray.num_dims m in
  let dims = Genarray.dims m |> Array.to_list |> CArray.of_list int |> CArray.start in
  let data = bigarray_start genarray m in
  __mat_of_bigarray num_dims dims data

let __mat_num_dims = foreign "mat_num_dims" (voidp @-> returning int)
let __mat_dims = foreign "mat_dims" (voidp @-> returning (ptr int))
let __mat_data = foreign "mat_data" (voidp @-> returning (ptr int))

let bigarray_of_cmat (m : cmat) : t =
  let num_dims = __mat_num_dims m in
  let dims_arr = __mat_dims m in
  let dims = CArray.from_ptr dims_arr num_dims |> CArray.to_list |> Array.of_list in
  let data = __mat_data m in
  bigarray_of_ptr genarray dims Int8_unsigned data

let __copy_cmat_bigarray =
  foreign "copy_mat_bigarray" (voidp @-> voidp @-> returning void)

let copy_cmat_bigarray (m1 : cmat) (m2 : t) =
  let root = Root.create m2 in
  let res = __copy_cmat_bigarray m1 root
  in Root.release root; res

let __create = foreign "create_mat" (void @-> returning voidp)
let __copy = foreign "mat_copy" (voidp @-> voidp @-> returning void)

let recycling = ref []

let finaliser value =
  recycling := value :: !recycling

let create () =
    (*
     * Instead of allowing mats to be freed, we keep a pool
     * of "recyclable" mats for re-use by future invocations
     * of Mat.create. This conveniently solves a couple of
     * problems at once.
     *
     * First, many programs that create lots of mats probably do
     * so as part of a loop, such as reading from a video file.
     * It is a bit inefficient to destroy and recreate the mat
     * every iteration. Using a mat pool should give us
     * significant reductions in memory allocation and therefore
     * better performance.
     *
     * Second, OpenCV has its own mechanism for garbage collection
     * of mats that interferes with OCaml's garbage collector.
     * There were significant issues with double-free errors.
     * This solution solves the problem by preventing the OCaml
     * GC from ever trying to free a mat.
     *
     * We only add a mat to the recycling list when the OCaml GC
     * tries to run, which ensures that the OCaml GC never frees
     * the mat and that the mat is no longer in scope in the
     * program (the GC only runs on unreachable values).
     *
     * This approach feels really dirty but it's almost too good
     * to be true so we are going to roll with it for now.
    *)
  match !recycling with
    | [] ->
        begin
          let mat = __create () |> bigarray_of_cmat in
          Gc.finalise finaliser mat;
          mat
        end
    | hd :: tl ->
        begin
          recycling := tl;
          Gc.finalise finaliser hd;
          hd
        end

let clone mat =
  let mat' = create () in
  let cmat' = cmat_of_bigarray mat' in
  __copy (cmat_of_bigarray mat) cmat';
  copy_cmat_bigarray cmat' mat';
  mat'
