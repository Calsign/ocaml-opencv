
open Opencv

let () =
  let vid = Video_capture.video_capture2 "test.mp4" 0 in
  let mat = Mat.create () in
  let chan = Mat.create () in
  (* let s = get_structuring_element 0 {width=11; height=11} {x=(-1); y=(-1)} in *)
  (* let () = get_text_size "hello" 10 10.0 10 10 |> ignore in *)
  let rec loop () =
    Video_capture.read1 vid (Cvdata.Mat mat) |> ignore;
    extract_channel (Cvdata.Mat mat) (Cvdata.Mat chan) 0;
    (* let rect = bounding_rect (Cvdata.Mat chan) in *)
    let b = 30 in
    let padded = Owl.Dense.Ndarray.Generic.pad ~v:0 [[b; b]; [b; b]; [0; 0]] mat in
    imshow "foobar" (Cvdata.Mat padded);
    (* let arr3 = chan |> array3_of_genarray in
     * Array3.get arr3 0 0 0 |> string_of_int |> print_endline;
     * let dims = Genarray.dims chan in
     * Array.iter (fun x -> x |> string_of_int |> print_endline) dims;
     * print_endline ""; *)
    wait_key 0 |> ignore;
    loop ()
  in loop ()
