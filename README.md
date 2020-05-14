
[OpenCV](http://opencv.org/) bindings for [OCaml](http://ocaml.org/).

## Quick start

Run `make` to install the library with ocamlfind. You must have OpenCV
installed on your system.

Run `make demos/basic` to run the demo. This demo requires you to
provide a video file `demos/basic/test.mp4` as input. It also requires
you to install the `owl` opam package.

Run `make docs` to generate documentation. Open
`opencv.docdir/index.html` to view.

## Goals

 - Provide access to the full OpenCV API through OCaml
 - Make it possible to use OpenCV API calls as pure functions
 - Use auto-generation of bindings as much as possible

## Caveats

The bindings are currently for a small subset of the OpenCV API (core,
imgproc, videoio, and highgui), but the plan is to eventually support
the entire API.

Tested with OpenCV 4.3.0. Should work fine with any OpenCV 4.x, but
modifications may be necessary to work with older versions.

OWL is not required to use the OpenCV bindings, but it is recommended
because the mat type is compatible with OWL type
`Dense.Ndarray.Generic`; OWL serves a role similar to numpy for Python.
