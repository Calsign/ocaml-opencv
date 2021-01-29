
open Opencv

module O = Owl.Dense.Ndarray.Generic

let () =
  let vid = Video_capture.video_capture2 "test.mp4" in
  (* let _ = get_text_size "hello" 10 10.0 10 10 in *)
  let rec loop () =
    let mat, _ = Video_capture.read vid in
    let lab = cvt_color mat ~~`COLOR_BGR2Lab in
    let lab_l = extract_channel lab 0 in
    let blurred = gaussian_blur lab_l {width=21; height=21} 10. in
    let threshed, _ = threshold blurred 100. 200. ~~`THRESH_BINARY in
    let contours, _ = find_contours threshed ~~`RETR_EXTERNAL ~~`CHAIN_APPROX_SIMPLE in
    let rect = bounding_rect threshed in
    let drawn = Draw.draw [
        Draw.rectangle2 rect (Scalar.color1 255.) ~thickness:2;
        Draw.draw_contours contours (-1) (Scalar.color1 0.) ~thickness:4;
      ] blurred in
    (* let _ = calc_hist [lab_l] [0] threshed [10] [0.; 255.] in *)
    let b = 30 in
    let tiled = O.concatenate ~axis:1 Cvdata.[|to_mat drawn; to_mat threshed|] in
    let padded = O.pad ~v:127 [[b; b]; [b; b]; [0; 0]] tiled in
    imshow "foobar" (Cvdata.Mat padded);
    let _ = wait_key () in
    loop ()
  in loop ()
