
open Opencv

let () =
  let vid = Video_capture.video_capture2 "test.mp4" ~~`CAP_ANY in
  (* let _ = get_text_size "hello" 10 10.0 10 10 in *)
  let rec loop () =
    let mat, _ = Video_capture.read1 vid in
    let lab = cvt_color mat ~~`COLOR_BGR2Lab 0 in
    let lab_l = extract_channel lab 0 in
    let blurred = gaussian_blur lab_l {width=21; height=21} 10. 10. 0 in
    let threshed, _ = threshold blurred 100. 200. ~~`THRESH_BINARY in
    let rect = bounding_rect threshed in
    let drawn = rectangle1 blurred rect (color1 255.) 2 ~~`FILLED 0 in
    (* let _ = calc_hist lab_l [0] threshed [10] [0.; 255.] true in *)
    let b = 30 in
    let tiled = Owl.Dense.Ndarray.Generic.concatenate ~axis:1
        [|drawn |> Cvdata.to_mat; threshed |> Cvdata.to_mat|] in
    let padded = Owl.Dense.Ndarray.Generic.pad ~v:127 [[b; b]; [b; b]; [0; 0]] tiled in
    imshow "foobar" (Cvdata.Mat padded);
    let _ = wait_key 0 in
    loop ()
  in loop ()
