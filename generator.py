#!/usr/bin/env python3

import sys
import os
from io import StringIO
import re

# from OpenCV
import hdr_parser
# custom thing for handling C++ types
import type_manager

src_files = [
    '/usr/include/opencv4/opencv2/core/types.hpp',
    '/usr/include/opencv4/opencv2/core/mat.hpp',
    '/usr/include/opencv4/opencv2/core.hpp',
    '/usr/include/opencv4/opencv2/imgproc.hpp',
    '/usr/include/opencv4/opencv2/videoio.hpp',
    '/usr/include/opencv4/opencv2/highgui.hpp',
]

c_reserved = {
    'sqrt': 'cv_sqrt',
    'pow': 'cv_pow',
    'exp': 'cv_exp',
    'log': 'cv_log',
}

ocaml_reserved = {
    'open': 'cv_open',
    'val': 'cv_val',
    'method': 'cv_method',
    'type': 'cv_type',
}

class StructVal():
    def __init__(self, val_type, c_name, ocaml_name=None):
        self.c_name = c_name
        self.ocaml_name = ocaml_name if ocaml_name is not None else c_name
        self.val_type = val_type

class Struct():
    def __init__(self, c_name, ocaml_name, values):
        self.c_name = c_name
        self.ocaml_name = ocaml_name
        self.values = values

    def ocaml2c_name(self):
        return '{}_ocaml2c'.format(self.ocaml_name)

    def c2ocaml_name(self):
        return '{}_c2ocaml'.format(self.ocaml_name)

    def ocaml_ctypes_name(self):
        return '{}_type'.format(self.ocaml_name)

structs = [
    Struct('Point', 'point2i', [StructVal('int', 'x'), StructVal('int', 'y')]),
    #Struct(['Point2f', 'Point2d'], 'point2f', [StructVal('float', 'x'), StructVal('float', 'y')]),
    Struct('Point2f', 'point2f', [StructVal('float', 'x'), StructVal('float', 'y')]),
    Struct('Rect', 'rect', [StructVal('int', 'x'), StructVal('int', 'y'),
                            StructVal('int', 'width'), StructVal('int', 'height')]),
    Struct('Size', 'size', [StructVal('int', 'width'), StructVal('int', 'height')]),
]

class Parameter():
    def __init__(self, name, ocaml_name, arg_type, default_value, output):
        self.name = name
        self.ocaml_name = ocaml_name
        self.arg_type = arg_type
        self.default_value = default_value
        self.output = output

    def __str__(self):
        return '{} : {} = {} ; {}'.format(self.name, self.arg_type,
                                          self.default_value, 'Output'
                                          if self.output else '')

class Function():
    def __init__(self, cpp_name, c_name, ocaml_name,
                 return_type, parameters, c_params, docs):
        self.cpp_name = cpp_name
        self.c_name = c_name
        self.ocaml_name = ocaml_name
        self.return_type = return_type
        self.parameters = parameters
        self.c_params = c_params
        self.docs = docs

    def __str__(self):
        return '{} : {}{}'.format(self.name, self.return_type,
                                  '\n    '.join([''] +
                                                [str(param)
                                                 for param in self.parameters]))

class EnumConstr():
    def __init__(self, cpp_name, ocaml_name, cpp_value, ocaml_value):
        self.cpp_name = cpp_name
        self.ocaml_name = ocaml_name
        self.cpp_value = cpp_value
        self.ocaml_value = ocaml_value

    def __str__(self):
        return self.ocaml_name

class Enum():
    def __init__(self, name, values, docs):
        self.name = name
        self.values = values
        self.docs = docs

    def __str__(self):
        return '{} ; {}'.format(self.name, self.values)

class Class():
    def __init__(self, cpp_name, qualified_cpp_name, c_name,
                 ocaml_name, ocaml_type, ctypes_name,
                 ctypes_type, inherits, docs, public_type=False):
        self.cpp_name = cpp_name
        self.qualified_cpp_name = qualified_cpp_name
        self.c_name = c_name
        self.ocaml_name = ocaml_name
        self.ocaml_type = ocaml_type
        self.ctypes_name = ctypes_name
        self.ctypes_type = ctypes_type
        self.inherits = inherits
        self.docs = docs
        self.public_type = public_type

        self.functions = []

    def add_function(self, function):
        self.functions.append(function)

    def __str__(self):
        return self.name

def read_file(fname):
    with open(fname, 'r') as f:
        def clean(line):
            if line.endswith('\n'):
                return line[:-1]
            else:
                return line
        return map(clean, f.readlines())

module_extras = {
    #'Mat': (read_file('incl/mat.ml.incl'), read_file('incl/mat.mli.incl')),
}

class_customizations = {
    #'Mat': {
    #    'ocaml_type': '(int, int8_unsigned_elt, c_layout) Genarray.t',
    #    'public_type': True,
    #    'c2ocaml': '(Mat.bigarray_of_cmat ({}))',
    #    'ocaml2c': '(Mat.cmat_of_bigarray ({}))',
    #    'post_action': "Mat.copy_cmat_bigarray {0}' {0}",
    #},
}

masked_modules = ['Mat']

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')

def camel_case(name):
    return all_cap_re.sub(r'\1_\2', first_cap_re.sub(r'\1_\2', name)).lower()

class FileWriter():
    def __init__(self, path, name, spaces_per_indent=2):
        self.buf = StringIO()
        self.path = path
        self.name = name
        self.spaces_per_indent = spaces_per_indent
        self.current_indent = ''

    def write(self, s=''):
        self.buf.write(self.current_indent)
        self.buf.write(s)
        self.buf.write('\n')

    def write_all(self, lines):
        for line in lines:
            self.write(line)

    def indent(self):
        self.current_indent += ' ' * self.spaces_per_indent

    def unindent(self):
        if len(self.current_indent) < self.spaces_per_indent:
            raise Exception('Trying to unindent too many times!')
        self.current_indent = self.current_indent[:-self.spaces_per_indent]

    def save(self):
        with open(os.path.join(self.path, self.name), 'wt') as f:
            f.write(self.buf.getvalue())

def convert_name(name):
    # strip 'cv.' prefix
    if name.startswith('cv.'):
        name = name[3:]

    c_name = name

    # remap blacklisted functions (typically conflicting built-ins)
    if name in c_reserved:
        c_name = c_reserved[c_name]

    # rename overloaded functions to prevent conflicts
    if c_name in overload_counts:
        overload_counts[c_name] += 1
        suffix = str(overload_counts[c_name])
        c_name = c_name + suffix
        ocaml_name = name + suffix
    else:
        overload_counts[c_name] = 0
        ocaml_name = name

    # convert to camel case
    ocaml_name = camel_case(ocaml_name)

    if ocaml_name in ocaml_reserved:
        ocaml_name = ocaml_reserved[ocaml_name]

    return (name, c_name, ocaml_name)

def sanitize_docs(docs):
    # don't terminate comments and don't start string literals
    return docs.replace('*)', '* )').replace('{|', '{ |')

if __name__ == '__main__':
    dest = sys.argv[1]
    print('Output directory: {}'.format(dest))

    # TODO enable UMat support, and make a wrapper for handling both Mat and UMat identically
    generate_umat = False

    parser = hdr_parser.CppHeaderParser(generate_umat_decls=generate_umat, generate_gpumat_decls=generate_umat)
    functions = []
    enums = []
    enum_map = {}
    classes = {}
    overload_counts = {}

    def add_struct(struct):
        def add_c_name(c_name):
            qual_name = 'cv::' + c_name
            c2ocaml = '({} ({{}}))'.format(struct.c2ocaml_name())
            ocaml2c = '({} ({{}}))'.format(struct.ocaml2c_name())
            # c2ocaml_ptr = '({} (!@ ({{}}))))'.format(struct.c2ocaml_name())
            # ocaml2c_ptr = '(allocate {} ({} ({{}})))'.format(struct.ocaml_ctypes_name(), struct.ocaml2c_name())

            # type_map[c_name] = TypeConversion(qual_name, qual_name, struct.ocaml_name,
            #                                   struct.ocaml_ctypes_name(), c2ocaml=c2ocaml, ocaml2c=ocaml2c)
            # type_map[c_name + '*'] = TypeConversion(qual_name + '*', qual_name + '*',
            #                                         struct.ocaml_name, 'ptr {}'.format(struct.ocaml_ctypes_name()),
            #                                         c2ocaml=c2ocaml_ptr, ocaml2c=ocaml2c_ptr)
            type_manager.add_type(type_manager.CustomType(
                qual_name, qual_name, struct.ocaml_ctypes_name(),
                struct.ocaml_ctypes_name(), struct.ocaml_name,
                ctypes2ocaml=c2ocaml, ocaml2ctypes=ocaml2c), silent_on_exists=True)

        if isinstance(struct.c_name, list):
            for c_name in struct.c_name:
                add_c_name(c_name)
        else:
            add_c_name(struct.c_name)

    for struct in structs:
        add_struct(struct)

    def add_enum(decl):
        def build_enum_constr(arg):
            cpp_name = arg[0].rsplit(' ', 1)[1]
            ocaml_name = cpp_name[cpp_name.rindex('.') + 1:]
            cpp_value = arg[1]
            try:
                ocaml_value = str(int(cpp_value))
            except ValueError:
                ocaml_value = 'failwith "constant {} is broken"'.format(ocaml_name)
            return EnumConstr(cpp_name, ocaml_name, cpp_value, ocaml_value)
        values = list(map(build_enum_constr, decl[3]))
        enums.append(Enum(decl[0].rsplit(' ', 1)[1], values, decl[5]))
        for constr in values:
            enum_map[constr.ocaml_name] = constr

    def add_class(decl):
        full_class_name = decl[0].rsplit(' ', 1)[1]
        name, c_name, ocaml_name = convert_name(full_class_name)
        inherits = decl[1].rsplit('::', 1)[1] if len(decl[1]) > 0 else None

        cpp_name = name
        qualified_cpp_name = 'cv::' + name + "*"
        c_name = 'cv::' + c_name + "*"
        ctypes_name = ocaml_name + '_type'
        ocaml_name = ocaml_name.capitalize()

        if ocaml_name in masked_modules:
            return

        # these can be modified per-class with class_customizations
        params = {
            'ctypes_type': 'ptr void',
            'ocaml_type': 'unit ptr',
            'public_type': False,
            'c2ocaml': '{}',
            'ocaml2c': '{}',
            'post_action': None,
        }

        if ocaml_name in class_customizations:
            params.update(class_customizations[ocaml_name])

        if full_class_name.startswith('cv.'):
            full_class_name = full_class_name[3:]
        classes[full_class_name] = \
            Class(cpp_name, qualified_cpp_name, c_name, ocaml_name, params['ocaml_type'],
                  ctypes_name, params['ctypes_type'], inherits, decl[5],
                  public_type=params['public_type'])
        type_manager.add_type(type_manager.CustomType(
            qualified_cpp_name, c_name, ctypes_name, ctypes_name, ocaml_name + '.t',
            ctypes2ocaml=params['c2ocaml'], ocaml2ctypes=params['ocaml2c'],
            post=params['post_action']), silent_on_exists=True)

    def add_function(decl):
        if decl[1] is None:
            decl[1] = 'void'

        name, c_name, ocaml_name = convert_name(decl[0])

        def sanitize_param(param):
            param = param.lower()
            if param in ocaml_reserved:
                param = ocaml_reserved[param]
            return param

        # extract function parameters
        params = [Parameter(arg[1], sanitize_param(arg[1]), arg[0],
                            arg[2] if len(arg[2]) > 0 else None,
                            '/O' in arg[3]) for arg in decl[3]]

        if '.' in name:
            # class method
            cls = name.rsplit('.', 1)[0]
            if cls in classes:
                name = name.rsplit('.', 1)[1]
                c_name = c_name.replace('.', '_')
                ocaml_name = convert_name(name)[2]

                c_params = params[:]

                if name == classes[cls].cpp_name:
                    # constructor
                    name = 'new cv::' + name
                    return_type = classes[cls].cpp_name + "*"
                else:
                    if '/S' in decl[2]:
                        # static method
                        name = 'cv::' + classes[cls].cpp_name + '::' + name
                    else:
                        name = '__self->' + name
                        params.insert(0, Parameter('__self', '__self', cls + "*", None, False))
                        
                    return_type = decl[1]
                        
                classes[cls].add_function(Function(name, c_name, ocaml_name, return_type, params, c_params, decl[5]))
            else:
                print('ERROR: Missing class: {}'.format(cls))
        else:
            functions.append(Function('cv::' + name, c_name, ocaml_name, decl[1], params, params, decl[5]))

    decls = []
    for hname in src_files:
        decls += parser.parse(hname, wmode=False)

    # first pass to collect classes and add types
    for decl in decls:
        if decl[0].startswith('enum'):
            # there's something screwy that happens where sometimes classes show up as enums
            # this is a really hacky way to make it work
            if decl[0].endswith('.<unnamed>'):
                decl[0] = decl[0][:-10]
                full_class_name = decl[0].rsplit(' ', 1)[1]
                if full_class_name.startswith('cv.'):
                    full_class_name = full_class_name[3:]
                if not full_class_name in classes:
                    add_class(decl)
            add_enum(decl)
        elif decl[0].startswith('class'):
            add_class(decl)
        else:
            pass

    # second pass to collect functions and methods
    for decl in decls:
        if decl[0].startswith('enum'):
            pass
        elif decl[0].startswith('class'):
            pass
        else:
            add_function(decl)

    missing_types = set()

    path = os.path.join(os.getcwd(), dest)

    opencv_h = FileWriter(path, 'opencv.h')
    opencv_cpp = FileWriter(path, 'opencv.cpp')
    opencv_ml = FileWriter(path, 'opencv.ml')
    opencv_mli = FileWriter(path, 'opencv.mli')

    opencv_h.write('#include <opencv2/opencv.hpp>')
    opencv_h.write('#include <opencv2/core.hpp>')
    opencv_h.write('#include <opencv2/imgproc.hpp>')
    opencv_h.write()
    opencv_h.write('#include "../glue.h"')
    opencv_h.write()
    opencv_h.write('extern "C" {')
    opencv_h.indent()

    opencv_cpp.write('#include "opencv.h"')
    opencv_cpp.write()
    opencv_cpp.write('extern "C" {')
    opencv_cpp.indent()

    opencv_ml.write('open Bigarray')
    opencv_ml.write()
    opencv_ml.write('open Ctypes')
    opencv_ml.write('open Foreign')
    opencv_ml.write('open Ctypes_static')
    opencv_ml.write()
    opencv_ml.write('include Glue')
    opencv_ml.write()
    #opencv_ml.write('let lib_opencv = Dl.dlopen ~filename:"libocamlopencv.so" ~flags:[]')
    #opencv_ml.write('let foreign = foreign ~from:lib_opencv')
    opencv_ml.write()

    opencv_mli.write('open Bigarray')
    opencv_mli.write('open Ctypes')
    opencv_mli.write()
    opencv_mli.write('open Glue')
    opencv_mli.write()

    def write_struct(struct):
        decl_fields = '; '.join(['{} : {}'
                                 .format(val.ocaml_name,
                                         type_manager.get_type(val.val_type)
                                         .get_ctypes_type())
                                 for val in struct.values])
        type_decl = 'type {} = {{ {} }}'.format(struct.ocaml_name, decl_fields)

        opencv_mli.write(type_decl)
        opencv_mli.write()

        opencv_ml.write(type_decl)
        opencv_ml.write('let {} : {} structure typ = structure "{}"'
                        .format(struct.ocaml_ctypes_name(), struct.ocaml_name, struct.c_name))
        for field in struct.values:
            opencv_ml.write('let {}_{} = field {} "{}" {}'
                            .format(struct.ocaml_name, field.ocaml_name,
                                    struct.ocaml_ctypes_name(), field.c_name,
                                    type_manager.get_type(field.val_type).get_ctypes_type()))
        opencv_ml.write('let () = seal {}'.format(struct.ocaml_ctypes_name()))
        opencv_ml.write('let {} x : {} ='.format(struct.c2ocaml_name(), struct.ocaml_name))
        opencv_ml.indent()
        opencv_ml.write('{')
        opencv_ml.indent()
        for field in struct.values:
            opencv_ml.write('{} = getf x {}_{};'
                            .format(field.ocaml_name, struct.ocaml_name, field.ocaml_name))
        opencv_ml.unindent()
        opencv_ml.write('}')
        opencv_ml.unindent()
        opencv_ml.write('let {} x : {} structure ='
                        .format(struct.ocaml2c_name(), struct.ocaml_name))
        opencv_ml.indent()
        opencv_ml.write('let y = make {} in'.format(struct.ocaml_ctypes_name()))
        for field in struct.values:
            opencv_ml.write('setf y {}_{} x.{};'
                            .format(struct.ocaml_name, field.ocaml_name, field.ocaml_name))
        opencv_ml.write('y')
        opencv_ml.unindent()

        # ctypes_type = ' @-> '.join([type_map[field.val_type].ctypes_type
        #                             for field in struct.values])
        # ctypes_type += ' @-> returning (ptr void)'
        # opencv_ml.write('let {} = foreign "{}" ({})'
        #                 .format(struct.ocaml2c_name(), struct.ocaml2c_name(), ctypes_type))
        opencv_ml.write()

    def write_enum(enum):
        name = enum.name
        if name.startswith('cv.'):
            name = name[3:]
        # catch all anonymous enums
        if name in classes:
            name = None
        if name == 'cv':
            name = None
        if name is not None:
            name = camel_case(name)
            name = name.replace('.', '_')
            if name.startswith('_'):
                name = name[1:]

        if name is not None:
            opencv_ml.write('type {} = ['.format(name))
            opencv_ml.indent()
            opencv_ml.indent()

            opencv_mli.write('type {} = ['.format(name))
            opencv_mli.indent()
            opencv_mli.indent()

            for constr in enum.values:
                opencv_ml.write('| `{}'.format(constr.ocaml_name))
                opencv_mli.write('| `{}'.format(constr.ocaml_name))

            opencv_ml.unindent()
            opencv_ml.write(']')
            opencv_ml.unindent()
            opencv_ml.write()

            opencv_mli.unindent()
            opencv_mli.write(']')
            opencv_mli.unindent()
            opencv_mli.write()

    def write_enum_converter():
        opencv_mli.write('type cv_const = [')
        opencv_mli.indent()
        opencv_mli.indent()

        opencv_ml.write('type cv_const = [')
        opencv_ml.indent()
        opencv_ml.indent()

        for name in enum_map:
            opencv_mli.write('| `{}'.format(name))
            opencv_ml.write('| `{}'.format(name))

        opencv_mli.unindent()
        opencv_mli.write(']')
        opencv_mli.unindent()
        opencv_mli.write()

        opencv_ml.unindent()
        opencv_ml.write(']')
        opencv_ml.unindent()
        opencv_ml.write()

        opencv_mli.write()
        opencv_mli.write('val int_of_cv_const : cv_const -> int')
        opencv_mli.write('val (~~) : cv_const -> int')
        opencv_mli.write()

        opencv_ml.write('let int_of_cv_const = function')
        opencv_ml.indent()

        for name, constr in enum_map.items():
            opencv_ml.write('| `{} -> {}'.format(constr.ocaml_name, constr.ocaml_value))

        opencv_ml.write('| _ -> failwith "unrecognized cv constant"')
        opencv_ml.unindent()
        opencv_ml.write()
        opencv_ml.write('let (~~) = int_of_cv_const')
        opencv_ml.write()

    def write_function(function, enclosing_module=None, mli_only=False):
        if not type_manager.has_type(function.return_type):
            print('Skipping {} because return type {} not in type map'.format(function.cpp_name, function.return_type))
            missing_types.add(function.return_type)
            return
        for param in function.parameters:
            if not type_manager.has_type(param.arg_type):
                print('Skipping {} because param type {} not in type map'.format(function.cpp_name, param.arg_type))
                missing_types.add(param.arg_type)
                return

        def check_enclosing_module(name):
            #return name[len(enclosing_module) + 1:] if enclosing_module is not None \
            #    and name.startswith(enclosing_module + '.') else name
            return name.replace('{}.t'.format(enclosing_module), 't')

        params_h = ', '.join(['{} {}'
                              .format(type_manager.get_type(param.arg_type).get_c_type(),
                                      param.name) for param in function.parameters])
        stub = '{} {}({})'.format(type_manager.get_type(function.return_type).get_cpp_type(),
                                  function.c_name, params_h)

        if not mli_only:
            opencv_h.write('{};'.format(stub))

        params_cpp = ', '.join([type_manager.get_type(param.arg_type)
                                .c_to_cpp(param.name) for param in function.c_params])
        value = '{}({})'.format(function.cpp_name, params_cpp)
        return_or_not = 'return ' if function.return_type != 'void' else ''

        if not mli_only:
            opencv_cpp.write('{} {{'.format(stub))
            opencv_cpp.indent()
            opencv_cpp.write('{}{};'.format(return_or_not,
                                            type_manager.get_type(function.return_type)
                                            .cpp_to_c(value)))
            opencv_cpp.unindent()
            opencv_cpp.write('}')

        param_names = [param.ocaml_name for param in function.parameters]
        param_names_prime = ["{}'".format(param.ocaml_name) for param in function.parameters]
        if len(param_names) == 0:
            param_names.append('()')
            param_names_prime.append('()')

        ctypes_sig_list = [type_manager.get_type(param.arg_type).get_ctypes_value()
                           for param in function.parameters]
        if len(ctypes_sig_list) == 0:
            ctypes_sig_list.append('void')
        ctypes_sig_list.append('returning ({})'
                               .format(type_manager.get_type(function.return_type)
                                       .get_ctypes_value()))
        ctypes_sig = ' @-> '.join(ctypes_sig_list)

        if not mli_only:
            opencv_ml.write('let __{} = foreign "{}" ({})'
                            .format(function.ocaml_name, function.c_name, ctypes_sig))
            opencv_ml.write('let {} {} ='
                            .format(function.ocaml_name, ' '.join(param_names)))
            opencv_ml.indent()
            for param in function.parameters:
                opencv_ml.write("let {}' = {} in"
                                .format(param.ocaml_name,
                                        type_manager.get_type(param.arg_type)
                                        .ocaml_to_ctypes(param.ocaml_name)))
            opencv_ml.write('let res = {} in'
                            .format(type_manager.get_type(function.return_type)
                                    .ctypes_to_ocaml('__{} {}'
                                                .format(function.ocaml_name,
                                                        ' '.join(param_names_prime)))))
            for param in function.parameters:
                post_func = type_manager.get_type(param.arg_type) \
                                        .ocaml_to_ctypes(param.ocaml_name).post
                if post_func is not None:
                    post = post_func(param.ocaml_name, "{}'".format(param.ocaml_name))
                    opencv_ml.write('{};'.format(post))
            opencv_ml.write('res')
            opencv_ml.unindent()

        ocaml_sig_list = [check_enclosing_module(
            type_manager.get_type(param.arg_type).get_ocaml_type())
                          for param in function.parameters]
        if len(ocaml_sig_list) == 0:
            ocaml_sig_list.append('unit')
        ocaml_sig_list.append(check_enclosing_module(
            type_manager.get_type(function.return_type).get_ocaml_type()))
        ocaml_sig = ' -> '.join(ocaml_sig_list)

        if len(function.docs) > 0:
            opencv_mli.write()
            opencv_mli.write('(**')
            opencv_mli.write(sanitize_docs(function.docs))
            opencv_mli.write('*)')

        opencv_mli.write('val {} : {}'.format(function.ocaml_name, ocaml_sig))

    def write_class(cls):
        if len(cls.docs) > 0:
            opencv_mli.write()
            opencv_mli.write('(**')
            opencv_mli.write(sanitize_docs(cls.docs))
            opencv_mli.write('*)')

        opencv_ml.write()
        opencv_ml.write('let {} = {}'.format(cls.ctypes_name, cls.ctypes_type))
        opencv_ml.write('module {} = struct'.format(cls.ocaml_name))
        opencv_ml.indent()

        opencv_mli.write()
        opencv_mli.write('module {} : sig'.format(cls.ocaml_name))
        opencv_mli.indent()

        if cls.inherits is not None:
            if cls.inherits in classes:
                opencv_ml.write('include {}'.format(classes[cls.inherits].ocaml_name))

                # manual include
                opencv_mli.write('type t = {}'.format(cls.ocaml_type))
                for function in classes[cls.inherits].functions:
                    write_function(function, enclosing_module=classes[cls.inherits].qualified_cpp_name, mli_only=True)
            else:
                print('Class {} inherits from {}, but {} does not exist'.format(cls.cpp_name, cls.inherits, cls.inherits))
        else:
            opencv_ml.write('type t = {}'.format(cls.ocaml_type))
            if cls.public_type:
                opencv_mli.write('type t = {}'.format(cls.ocaml_type))
            else:
                opencv_mli.write('type t')

        if cls.ocaml_name in module_extras:
            opencv_ml.write_all(module_extras[cls.ocaml_name][0])
            opencv_mli.write_all(module_extras[cls.ocaml_name][1])

        for function in cls.functions:
            write_function(function, enclosing_module=cls.ocaml_name)

        opencv_ml.unindent()
        opencv_ml.write('end')

        opencv_mli.unindent()
        opencv_mli.write('end')

    opencv_ml.write_all(read_file('incl/mat.ml.incl'))
    opencv_mli.write_all(read_file('incl/mat.mli.incl'))

    opencv_ml.write_all(read_file('incl/cvdata.ml.incl'))
    opencv_mli.write_all(read_file('incl/cvdata.mli.incl'))

    for struct in structs:
        write_struct(struct)

    for cls in classes.values():
        write_class(cls)

    for function in functions:
        write_function(function)

    for enum in enums:
        write_enum(enum)

    write_enum_converter()

    opencv_h.unindent()
    opencv_h.write('}')

    opencv_cpp.unindent()
    opencv_cpp.write('}')

    opencv_h.save()
    opencv_cpp.save()
    opencv_ml.save()
    opencv_mli.save()

    print('Missing types:', missing_types)
