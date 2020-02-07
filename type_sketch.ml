
open Bigarray

type color_space =
  | BGR
  | LAB
  | LUV
  | HSV
  | GRAY

type mat = (int, int8_unsigned_elt, c_layout) Array3.t
type px = (int, int8_unsigned_elt, c_layout) Array1.t

type dim = int * int * int

let dim_of_mat (mat : mat) =
  Array3.(dim1 mat, dim2 mat, dim3 mat)

let string_of_dim (w, h, d) =
  Printf.sprintf "(%i, %i, %i)" w h d

let make_bigarray (w, h, d) =
  Array3.create Int8_unsigned c_layout w h d

let make_mat ?(c = BGR) w h : mat =
  let d = match c with
    | GRAY -> 1
    | _ -> 3 in
  make_bigarray (w, h, d)

let px mat x y : px =
  Array3.slice_left_1 mat x y

let array_of_px (px : px) =
  Array.init (Array1.dim px) (Array1.get px)

let px_of_array (arr : int array) =
  if Array.length arr != 1 && Array.length arr != 3
  then invalid_arg (Printf.sprintf "Invalid pixel array size: %i" (Array.length arr));
  Array1.of_array Int8_unsigned c_layout arr

let zeroes ?(c = BGR) w h =
  let mat = make_mat w h ~c in
  Array3.fill mat 0; mat

let elementwise (op : (int * int * int) -> unit) (w, h, d) =
  let open Array3 in
  for i = 0 to w do
    for j = 0 to h do
      for k = 0 to d do
        op (i, j, k)
      done
    done
  done

let construct_elementwise (op : (int * int * int) -> int) dim =
  let open Array3 in
  let ret = make_bigarray dim in
  let func (i, j, k) =
    unsafe_set ret i j k (op (i, j, k)) in
  elementwise func dim; ret

let construct_px px dim =
  let _, _, d = dim in
  if (Array.length px) != d
  then invalid_arg (Printf.sprintf "Incompatible pixel size %i with dimension %s"
                      (Array.length px) (string_of_dim dim));
  let func (_, _, k) =
    px.(k) in
  construct_elementwise func dim

let zeros w h =
  construct_px [|0|] (w, h, 1)

let ones w h =
  construct_px [|255|] (w, h, 1)

let immutable_bitwise_binary (op : int -> int -> int) (mat1 : mat) (mat2 : mat) =
  let dim = dim_of_mat mat1 in
  let dim2 = dim_of_mat mat2 in
  if not (dim = dim2)
  then invalid_arg
      (Printf.sprintf "Incompatible dimensions: %s and %s"
         (string_of_dim dim) (string_of_dim dim2));
  let func (i, j, k) =
    op (Array3.unsafe_get mat1 i j k) (Array3.unsafe_get mat2 i j k) in
  construct_elementwise func dim

let immutable_bitwise_unary (op : int -> int) (mat : mat) =
  let dim = dim_of_mat mat in
  let func (i, j, k) =
    op (Array3.unsafe_get mat i j k) in
  construct_elementwise func dim

let ($&) = immutable_bitwise_binary (land)
let ($|) = immutable_bitwise_binary (lor)
let ($~) = immutable_bitwise_unary (lnot)
let ($^) = immutable_bitwise_binary (lxor)
