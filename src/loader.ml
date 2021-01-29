open Foreign

let lib_opencv =
  let lib = "dllopencv_stubs.so" in
  let paths =
    match Sys.getenv_opt "CAML_LD_LIBRARY_PATH" with
    | None -> []
    | Some path ->
       String.split_on_char ':' path
       |> List.map (fun s -> s ^ "/")
  in

  let rec load_opencv =
    function
    | path :: paths -> begin
        let filename = path ^ lib in
        try
          Dl.dlopen ~filename ~flags:[RTLD_NOW]
        with
        | _ ->
           load_opencv paths
      end
    | [] -> failwith ("Could not find library: " ^ lib)
  in
  load_opencv ("" :: paths)

let foreign = foreign ~from:lib_opencv
