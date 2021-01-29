
open Opencv

(* Same as regular demo, but using the API imperative-style. *)

let () =
  let vid = Video_capture.video_capture2 "test.mp4" in
  let mat = Cvdata.Mat (Mat.create ()) in
  let chan = Cvdata.Mat (Mat.create ()) in
  let threshed = Cvdata.Mat (Mat.create ()) in
  let rec loop () =
    let _ = Video_capture.read vid ~image:mat in
    let _ = cvt_color mat ~dst:mat ~~`COLOR_BGR2Lab in
    let _ = extract_channel mat ~dst:chan 0 in
    let _ = gaussian_blur chan ~dst:chan {width=21; height=21} 10. in
    let _ = threshold chan ~dst:threshed 100. 200. ~~`THRESH_BINARY in
    let rect = bounding_rect threshed in
    let _ = rectangle2 chan rect (Scalar.color1 255.) ~thickness:2 in
    let b = 30 in
    let tiled = Owl.Dense.Ndarray.Generic.concatenate ~axis:1
        [|chan |> Cvdata.to_mat; threshed |> Cvdata.to_mat|] in
    let padded = Owl.Dense.Ndarray.Generic.pad ~v:127 [[b; b]; [b; b]; [0; 0]] tiled in
    imshow "foobar" (Cvdata.Mat padded);
    let _ = wait_key () in
    loop ()
  in loop ()
