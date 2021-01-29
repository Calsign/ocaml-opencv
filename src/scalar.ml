open Ctypes_static

let foreign = Loader.foreign

type t = { w : float; x : float; y : float; z : float }

let __build_scalar = foreign "build_scalar"
                       (double @-> double @-> double @-> double @-> returning (ptr void))
let __scalar_w = foreign "scalar_w" (ptr void @-> returning double)
let __scalar_x = foreign "scalar_x" (ptr void @-> returning double)
let __scalar_y = foreign "scalar_y" (ptr void @-> returning double)
let __scalar_z = foreign "scalar_z" (ptr void @-> returning double)

let ocaml_to_ctypes s =
  __build_scalar s.w s.x s.y s.z

let ctypes_to_ocaml s =
  {
    w = __scalar_w s;
    x = __scalar_x s;
    y = __scalar_y s;
    z = __scalar_z s;
  }

let color1 w = { w; x = 0.; y = 0.; z = 0. }
let color2 w x = { w; x; y = 0.; z = 0. }
let color3 w x y = { w; x; y; z = 0. }
let color4 w x y z = { w; x; y; z }
