
open Opencv

let () =
  let vid = Video_capture.video_capture2 "test.mp4" ~~`CAP_ANY in
  let mat = Mat.create () in
  let chan = Mat.create () in
  let threshed = Mat.create () in
  let kernel = get_structuring_element ~~`MORPH_ELLIPSE {width=11; height=11} {x=(-1); y=(-1)} in
  Array.iter (fun d -> d |> string_of_int |> print_endline) (Bigarray.Genarray.dims kernel);
  (* let _ = get_text_size "hello" 10 10.0 10 10 in *)
  let rec loop () =
    let _ = Video_capture.read1 vid (Cvdata.Mat mat) in
    let _ = extract_channel (Cvdata.Mat mat) (Cvdata.Mat chan) 0 in
    let _ = threshold (Cvdata.Mat chan) (Cvdata.Mat threshed) 100. 200. ~~`THRESH_BINARY in
    let rect = bounding_rect (Cvdata.Mat threshed) in
    rectangle1 (Cvdata.Mat chan) rect (color1 255.) 2 ~~`FILLED 0;
    let total = sum (Cvdata.Mat chan) in
    print_endline (string_of_float total.w);
    let b = 30 in
    let tiled = Owl.Dense.Ndarray.Generic.concatenate ~axis:1 [|chan; threshed|] in
    let padded = Owl.Dense.Ndarray.Generic.pad ~v:127 [[b; b]; [b; b]; [0; 0]] tiled in
    imshow "foobar" (Cvdata.Mat padded);
    let _ = wait_key 0 in
    loop ()
  in loop ()
