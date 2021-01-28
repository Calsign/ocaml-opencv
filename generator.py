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
    'opencv4/opencv2/core/types.hpp',
    'opencv4/opencv2/core/mat.hpp',
    'opencv4/opencv2/core.hpp',
    'opencv4/opencv2/imgproc.hpp',
    'opencv4/opencv2/videoio.hpp',
    'opencv4/opencv2/highgui.hpp',
]

system_include_dir_search = [
    '/usr/include/',
    '/usr/local/include',
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
    'rec': 'rect',
}


class StructVal():
    def __init__(self, val_type_cpp_name, cpp_name, ocaml_name=None):
        self.cpp_name = cpp_name
        self.ocaml_name = ocaml_name if ocaml_name is not None else cpp_name
        self.val_type_cpp_name = val_type_cpp_name

    def get_val_type(self):
        return type_manager.get_type(self.val_type_cpp_name)


class Struct():
    def __init__(self, cpp_name, ocaml_name, values):
        self.clean_cpp_name = cpp_name.replace(
            '::', '').replace('<', '_').replace('>', '')
        self.cpp_name = cpp_name
        self.ocaml_name = ocaml_name
        self.values = values

    def ocaml2c_name(self):
        return '{}_ocaml2c'.format(self.ocaml_name)

    def c2ocaml_name(self):
        return '{}_c2ocaml'.format(self.ocaml_name)

    def c_constr_name(self):
        return '{}_constr'.format(self.clean_cpp_name)

    def c_getter_name(self, param):
        return '{}_get_{}'.format(self.clean_cpp_name, param.cpp_name)


structs = [
    Struct('cv::Point_<int>', 'point2i', [
           StructVal('int', 'x'), StructVal('int', 'y')]),
    Struct('cv::Point_<float>', 'point2f', [
           StructVal('float', 'x'), StructVal('float', 'y')]),
    Struct('cv::Point_<double>', 'point2d', [
           StructVal('double', 'x'), StructVal('double', 'y')]),
    Struct('cv::Rect_<int>', 'rect2i', [StructVal('int', 'x'), StructVal('int', 'y'),
                                        StructVal('int', 'width'), StructVal('int', 'height')]),
    Struct('cv::Size_<int>', 'size2i', [StructVal(
        'int', 'width'), StructVal('int', 'height')]),
    Struct('cv::Size_<float>', 'size2f', [StructVal(
        'float', 'width'), StructVal('float', 'height')]),
    Struct('cv::RotatedRect', 'rotated_rect', [StructVal('const Point_<float> &', 'center'),
                                               StructVal(
                                                   'const Size_<float> &', 'size'),
                                               StructVal('float', 'angle')]),
]

struct_aliases = {
    'Point': 'cv::Point_<int>',
    'Point2d': 'cv::Point_<double>',
    'Point2f': 'cv::Point_<float>',
    'Rect': 'cv::Rect_<int>',
    'Size': 'cv::Size_<int>',
}


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

    def get_default_val_c_name(self, enclosing_module, function_c_name):
        return '{}__{}__{}__default' \
            .format(('__{}'.format(enclosing_module)
                     if enclosing_module is not None else ''),
                    function_c_name, self.name)

    def get_default_val_ocaml_name(self, enclosing_module, function_ocaml_name):
        return '{}__{}__{}__default' \
            .format(('__{}'.format(enclosing_module)
                     if enclosing_module is not None else ''),
                    function_ocaml_name, self.ocaml_name)


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
        self.param_map = {
            param.name: param.ocaml_name for param in self.parameters}

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


masked_modules = ['Mat']

first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def snake_case(name):
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


def convert_name(name, is_function=True, create_ocaml_overload_counts=False,
                 parent_module=None):
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
        ocaml_name = name if is_function else name + suffix
    else:
        overload_counts[c_name] = 0
        ocaml_name = name

    # convert to camel case
    ocaml_name = snake_case(ocaml_name)

    # in this case we detect a class method and re-run this function anyway,
    # so don't screw up the overload counts
    if not ('.' in ocaml_name and is_function):
        overload_key = ocaml_name if parent_module is None \
            else parent_module + '.' + ocaml_name
        if overload_key in ocaml_overload_counts:
            ocaml_overload_counts[overload_key] += 1
            suffix = str(ocaml_overload_counts[overload_key])
            ocaml_name += suffix
        elif create_ocaml_overload_counts:
            ocaml_overload_counts[overload_key] = 0

    if ocaml_name in ocaml_reserved:
        ocaml_name = ocaml_reserved[ocaml_name]

    return (name, c_name, ocaml_name)


def sanitize_docs(docs, name=None, params=[], param_map={}, extra_unit=False):
    if name is not None:
        def get_param_name(param):
            if type_manager.get_type(param.arg_type).has_default_value() \
               or param.default_value is not None:
                fmt = '?{}'
            else:
                fmt = '{}'
            return fmt.format(param.ocaml_name)
        param_names = list(map(get_param_name, params))
        if extra_unit:
            param_names.append('()')
        usage = 'Usage: [{} {}]' \
            .format(name, ' '.join(param_names))
    else:
        usage = ''

    # a bunch of really jank things to make comments
    # parse-able by ocamldoc
    docs1 = re.sub(r'@code({.*?})?([\s\S]*?)@endcode', r'{[ \2 ]}', docs)
    docs2 = re.sub(r'\\f[\[\$]([\s\S]*?)\\f[\]\$]', r'{% \1 %}', docs1)
    docs3 = re.sub(r'\\f({.*?})([\s\S]*?)\\f}', r'{% \2 %}', docs2)

    def param_sub(match):
        cpp_name = match.group(2)
        if cpp_name in ocaml_reserved:
            cpp_name = ocaml_reserved[cpp_name]
        if cpp_name in param_map:
            out_name = param_map[cpp_name]
        else:
            print('Warning: param {} not found found for function {}'.format(
                cpp_name, name))
            out_name = cpp_name
        return '- Parameter: [{}]:'.format(out_name)
    docs4 = re.sub(r'@param(\[out\])?\s*([a-zA-Z0-9_]*)', param_sub, docs3)
    docs5 = re.sub(r'@return', r'- Returns:',
                   docs4.replace('@returns', '@return'))
    docs6 = re.sub(r'`(.*?)`', r'[\1]', docs5)
    docs7 = docs6.replace('*)', '* )') \
                 .replace('{|', '{ |') \
                 .replace('[out]', 'return') \
                 .replace('@see', 'See also') \
                 .replace('@brief ', '') \
                 .replace('@overload', '') \
                 .replace('@internal', '') \
                 .replace('@endinternal', '') \
                 .replace('@cite', '') \
                 .replace('@note', 'Note: ') \
                 .replace('@ref', '') \
                 .replace('@sa', 'See also: ') \
                 .replace('@todo', 'TODO') \
                 .replace('@snippet', 'Snippet:') \
                 .replace('@include', 'Include:') \
                 .replace('@anchor', '') \
                 .replace('@ingroup', 'Group:') \
                 .replace('@paramreturn', '@param') \
                 .replace('@b', '')

    if len(docs7) > 0:
        return usage + '\n\n' + docs7
    else:
        return usage


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('No output folder specified!')
        exit(1)

    dest = sys.argv[1]
    print('Output directory: {}'.format(dest))

    if len(sys.argv) > 2:
        system_include_dir_search.insert(0, sys.argv[2])

    system_include_dir = None
    for include_dir in system_include_dir_search:
        if os.path.exists(os.path.join(include_dir, src_files[0])):
            system_include_dir = include_dir
            break

    print('Using include dir: {}'.format(system_include_dir))

    # TODO enable UMat support, and make a wrapper for handling both Mat and UMat identically
    generate_umat = False

    parser = hdr_parser.CppHeaderParser(
        generate_umat_decls=generate_umat, generate_gpumat_decls=generate_umat)
    functions = []
    enums = []
    enum_map = {}
    defined_enum_consts = set()
    classes = {}
    overload_counts = {}
    ocaml_overload_counts = {}
    draw_functions = []

    def add_struct(struct):
        type_manager.add_type(type_manager.CustomType(
            struct.cpp_name, struct.cpp_name, 'unit ptr', 'ptr void', struct.ocaml_name,
            ctypes2ocaml='({} ({{}}))'.format(struct.c2ocaml_name()),
            ocaml2ctypes='({} ({{}}))'.format(struct.ocaml2c_name()),
            must_pointerize=True))

    for struct in structs:
        add_struct(struct)

    for alias, struct_name in struct_aliases.items():
        type_manager.add_type_alias(struct_name, alias)

    def add_enum(decl):
        def build_enum_constr(arg):
            cpp_name = arg[0].rsplit(' ', 1)[1]
            ocaml_name = cpp_name[cpp_name.rindex('.') + 1:]
            cpp_value = arg[1]
            try:
                ocaml_value = str(int(cpp_value))
            except ValueError:
                ocaml_value = 'failwith "constant {} is broken"'.format(
                    ocaml_name)
            return EnumConstr(cpp_name, ocaml_name, cpp_value, ocaml_value)
        values = list(map(build_enum_constr, decl[3]))
        enums.append(Enum(decl[0].rsplit(' ', 1)[1], values, decl[5]))
        for constr in values:
            enum_map[constr.ocaml_name] = constr

    def add_class(decl):
        full_class_name = decl[0].rsplit(' ', 1)[1]
        name, c_name, ocaml_name = convert_name(full_class_name, is_function=False)
        inherits = decl[1].rsplit('::', 1)[1] if len(decl[1]) > 0 else None

        cpp_name = name
        qualified_cpp_name = 'cv::' + name + "*"
        c_name = 'cv::' + c_name + "*"
        ctypes_name = ocaml_name + '_type'
        ocaml_name = ocaml_name.capitalize()

        if ocaml_name in masked_modules:
            return

        params = {
            'ctypes_type': 'ptr void',
            'ocaml_type': 'unit ptr',
            'public_type': False,
            'c2ocaml': '{}',
            'ocaml2c': '{}',
            'post_action': None,
        }

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
            param = snake_case(param)
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
                ocaml_name = convert_name(name, parent_module=cls)[2]

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
                        params.insert(0, Parameter(
                            '__self', '__self', cls + "*", None, False))

                    return_type = decl[1]

                classes[cls].add_function(
                    Function(name, c_name, ocaml_name, return_type, params, c_params, decl[5]))
            else:
                print('ERROR: Missing class: {}'.format(cls))
        else:
            functions.append(Function('cv::' + name, c_name,
                                      ocaml_name, decl[1], params, params, decl[5]))

    decls = []
    for hname in src_files:
        decls += parser.parse(os.path.join(system_include_dir, hname), wmode=False)

    # first pass to collect classes and add types
    for decl in decls:
        if decl[0].startswith('enum'):
            # there's something screwy that happens where sometimes classes
            # show up as enums, this is a really hacky way to make it work
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

    # second pass to identify overloaded OCaml functions
    for decl in decls:
        if decl[0].startswith('enum') or decl[0].startswith('class'):
            pass
        else:
            name, _, _ = convert_name(decl[0], create_ocaml_overload_counts=True)

            if '.' in name:
                # class method
                cls = name.rsplit('.', 1)[0]
                if cls in classes:
                    name = name.rsplit('.', 1)[1]
                    convert_name(name, create_ocaml_overload_counts=True,
                                 parent_module=cls)

    # only add numbers for functions that are actually overloaded
    ocaml_overload_counts = \
        {name: 0 for name, count in ocaml_overload_counts.items() if count > 0}

    # third pass to collect functions and methods
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
    opencv_h.write('#include "glue.h"')
    opencv_h.write()
    opencv_h.write('using namespace cv;')
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

    opencv_ml.write_all(read_file('incl/loader.ml.incl'))
    opencv_ml.write('let foreign = foreign ~from:lib_opencv')
    opencv_ml.write(
        'let foreign_value name typ = foreign_value ~from:lib_opencv name typ')
    opencv_ml.write()

    opencv_mli.write('open Bigarray')
    opencv_mli.write('open Ctypes')
    opencv_mli.write()

    opencv_ml.write_all(read_file('incl/vector.ml.incl'))
    opencv_mli.write_all(read_file('incl/vector.mli.incl'))

    opencv_ml.write_all(read_file('incl/scalar.ml.incl'))
    opencv_mli.write_all(read_file('incl/scalar.mli.incl'))

    def write_struct(struct):
        decl_fields = '; '.join(['{} : {}'
                                 .format(val.ocaml_name, val.get_val_type().get_ocaml_type())
                                 for val in struct.values])
        type_decl = 'type {} = {{ {} }}'.format(struct.ocaml_name, decl_fields)

        opencv_mli.write(type_decl)
        opencv_mli.write()

        opencv_ml.write(type_decl)
        opencv_ml.write()

        constr_ctypes = ' @-> '.join([field.get_val_type().get_ctypes_value()
                                      for field in struct.values])
        opencv_ml.write('let _{} = foreign "{}" ({} @-> returning (ptr void))'
                        .format(struct.c_constr_name(), struct.c_constr_name(), constr_ctypes))
        for field in struct.values:
            opencv_ml.write('let _{} = foreign "{}" (ptr void @-> returning ({}))'
                            .format(struct.c_getter_name(field), struct.c_getter_name(field),
                                    field.get_val_type().get_ctypes_value()))

        ocaml_params = ' '.join([field.get_val_type().ocaml_to_ctypes(
            's.{}'.format(field.ocaml_name)) for field in struct.values])
        opencv_ml.write('let {} s = _{} {}'.format(
            struct.ocaml2c_name(), struct.c_constr_name(), ocaml_params))

        opencv_ml.write('let {} s ='.format(struct.c2ocaml_name()))
        opencv_ml.indent()
        opencv_ml.write('{')
        opencv_ml.indent()
        for field in struct.values:
            opencv_ml.write('{} = {};'
                            .format(field.ocaml_name, field.get_val_type().ctypes_to_ocaml(
                                '_{} s'.format(struct.c_getter_name(field)))))
        opencv_ml.unindent()
        opencv_ml.write('}')
        opencv_ml.unindent()

        opencv_ml.write()

        cpp_params = ', '.join(['{} {}'.format(field.get_val_type().get_cpp_type(),
                                               field.cpp_name) for field in struct.values])
        opencv_h.write('{} *{}({});'.format(struct.cpp_name,
                                            struct.c_constr_name(), cpp_params))

        opencv_cpp.write('{} *{}({}) {{'.format(struct.cpp_name,
                                                struct.c_constr_name(), cpp_params))
        opencv_cpp.indent()
        opencv_cpp.write('return new {}({});'
                         .format(struct.cpp_name,
                                 ', '.join([field.cpp_name for field in struct.values])))
        opencv_cpp.unindent()
        opencv_cpp.write('}')

        for field in struct.values:
            opencv_h.write('{} {}({} *s);'.format(field.get_val_type().get_cpp_type(),
                                                  struct.c_getter_name(field), struct.cpp_name))
            opencv_cpp.write('{} {}({} *s) {{'.format(field.get_val_type().get_cpp_type(),
                                                      struct.c_getter_name(field), struct.cpp_name))
            opencv_cpp.indent()
            opencv_cpp.write('return s->{};'.format(field.cpp_name))
            opencv_cpp.unindent()
            opencv_cpp.write('}')

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
            name = snake_case(name)
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

        for constr in enum.values:
            if constr.ocaml_name not in defined_enum_consts and not constr.cpp_name.startswith('cv.Param'):
                defined_enum_consts.add(constr.ocaml_name)
                opencv_h.write('int __{} = (int) {};'
                               .format(constr.ocaml_name, constr.cpp_name.replace('.', '::')))
                opencv_ml.write('let __{} = foreign_value "__{}" int |> (!@)'
                                .format(constr.ocaml_name, constr.ocaml_name))

        opencv_h.write()
        opencv_ml.write()

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

        opencv_ml.write('let int_of_cv_const = function')
        opencv_ml.indent()

        for name, constr in enum_map.items():
            if constr.ocaml_name in defined_enum_consts:
                opencv_ml.write(
                    '| `{} -> __{}'.format(constr.ocaml_name, constr.ocaml_name))
            else:
                opencv_ml.write('| `{} -> failwith "constant `{} unsupported"'
                                .format(constr.ocaml_name, constr.ocaml_name))

        opencv_ml.write('| _ -> failwith "unrecognized cv constant"')
        opencv_ml.unindent()
        opencv_ml.write()

    def write_function(function, enclosing_module=None, mli_only=False):
        if not type_manager.has_type(function.return_type):
            print('Skipping {} because return type {} not in type map'.format(
                function.cpp_name, function.return_type))
            missing_types.add(function.return_type)
            return
        for param in function.parameters:
            if not type_manager.has_type(param.arg_type):
                print('Skipping {} because param type {} not in type map'.format(
                    function.cpp_name, param.arg_type))
                missing_types.add(param.arg_type)
                return

        def check_enclosing_module(name):
            # return name[len(enclosing_module) + 1:] if enclosing_module is not None \
            #    and name.startswith(enclosing_module + '.') else name
            return name.replace('{}.t'.format(enclosing_module), 't')

        def pointerize_type(typ, cpp=False):
            fmt = '{} *' if typ.must_pass_pointer() and not typ.is_pointer() else '{}'
            return fmt.format(typ.get_cpp_type() if cpp else typ.get_c_type())

        params_h = ', '.join(
            ['{} {}'.format(pointerize_type(type_manager.get_type(param.arg_type)),
                            param.name) for param in function.parameters])
        stub = '{} {}({})'.format(pointerize_type(type_manager
                                                  .get_type(function.return_type), cpp=True),
                                  function.c_name, params_h)

        if not mli_only:
            opencv_h.write('{};'.format(stub))

        draw_in_out_mat_count = 0

        # Keep track of number of default parameters.
        # If all of the parameters have default values, then we need
        # to add a unit to the end so that we can used properly (OCaml
        # functions where the last parameter is optional cannot be applied
        # without supplying that parameter)
        total_default_params = 0

        # default parameters
        for param in function.parameters:
            arg_type = type_manager.get_type(param.arg_type)
            draw_in_out_mat_count += arg_type.is_draw_function()

            if param.default_value is not None:
                c_name = param.get_default_val_c_name(
                    enclosing_module, function.c_name)
                ocaml_name = param.get_default_val_ocaml_name(
                    enclosing_module, function.ocaml_name)

                cpp_type = arg_type.get_cpp_type()
                pointerized_type = pointerize_type(arg_type, cpp=True)

                # There are screwy things with autoboxing rules and whatnot,
                # so the easiest thing for us to do here is put the default
                # value as a default argument in a helper function and then
                # call that function - that way it is the same syntactic
                # class as the header file from which it is pulled.

                opencv_h.write('{} {}();'.format(pointerized_type, c_name))

                opencv_cpp.write(
                    '{} _{}({} v = {}) {{'.format(cpp_type, c_name,
                                                  cpp_type, param.default_value))
                opencv_cpp.indent()
                opencv_cpp.write('return v;')
                opencv_cpp.unindent()
                opencv_cpp.write('}')

                opencv_cpp.write('{} {}() {{'.format(pointerized_type, c_name))
                opencv_cpp.indent()
                if arg_type.must_pass_pointer() and not arg_type.is_pointer():
                    opencv_cpp.write(
                        'return new {}(_{}());'.format(cpp_type, c_name))
                else:
                    opencv_cpp.write('return _{}();'.format(c_name))
                opencv_cpp.unindent()
                opencv_cpp.write('}')

                opencv_ml.write('let {} ='.format(ocaml_name))
                opencv_ml.indent()
                opencv_ml.write('let f = foreign "{}" (void @-> returning ({})) in'
                                .format(c_name, arg_type.get_ctypes_value()))
                opencv_ml.write('fun () -> let v = f () in {}'
                                .format(arg_type.ctypes_to_ocaml('v')))
                opencv_ml.unindent()

                total_default_params += 1
            elif type_manager.get_type(param.arg_type).has_default_value():
                total_default_params += 1

        def pointerize_value(typ, val):
            fmt = '*({})' if typ.must_pass_pointer() and not typ.is_pointer() else '{}'
            return fmt.format(typ.c_to_cpp(val))

        def depointerize_value(typ, val):
            pass

        params_cpp = ', '.join([pointerize_value(type_manager.get_type(param.arg_type),
                                                 param.name) for param in function.c_params])
        value = '{}({})'.format(function.cpp_name, params_cpp)
        ret_type = type_manager.get_type(function.return_type)

        if function.return_type == 'void':
            invoke_fmt = '{};'
        elif ret_type.must_pass_pointer() and not ret_type.is_pointer():
            invoke_fmt = 'return new {} ({{}});'.format(
                ret_type.get_cpp_type())
        else:
            invoke_fmt = 'return {};'

        if not mli_only:
            opencv_cpp.write('{} {{'.format(stub))
            opencv_cpp.indent()
            opencv_cpp.write(invoke_fmt.format(ret_type.cpp_to_c(value)))
            opencv_cpp.unindent()
            opencv_cpp.write('}')

        def get_param_name(param):
            typ = type_manager.get_type(param.arg_type)
            if param.default_value is not None:
                return '?({} = {} ())' \
                    .format(param.ocaml_name,
                            param.get_default_val_ocaml_name(enclosing_module,
                                                             function.ocaml_name))
            elif typ.has_default_value():
                return '?({} = {})'.format(param.ocaml_name, typ.get_default_value())
            else:
                return param.ocaml_name

        def is_optional_param(param):
            return type_manager.get_type(param.arg_type).has_default_value() \
                or param.default_value is not None

        # move (float) optional params to the front to prevent un-erasable optional arguments
        # (basically optional arguments can't be the last parameter in OCaml)
        floated_params = list(
            sorted(function.parameters, key=lambda param: not is_optional_param(param)))
        optional_param_count = len(list(filter(is_optional_param, function.parameters)))

        # add extra parameters for optionally disabling cloning of cloneable params
        inserted_param_count = 0
        for i, param in enumerate(floated_params.copy()):
            if type_manager.get_type(param.arg_type).is_cloneable():
                floated_params.insert(i + inserted_param_count,
                                      Parameter('', '{}_recycle'
                                                .format(param.ocaml_name),
                                                '__recycle_flag', None, False))
                inserted_param_count += 1

        floated_param_names = list(map(get_param_name, floated_params))
        param_names_prime = ["{}'".format(
            param.ocaml_name) for param in function.parameters]
        if len(function.parameters) <= total_default_params:
            floated_param_names.append('()')
        if len(function.parameters) == 0:
            param_names_prime.append('()')

        ctypes_sig_list = [type_manager.get_type(param.arg_type).get_ctypes_value()
                           for param in function.parameters]
        if len(ctypes_sig_list) == 0:
            ctypes_sig_list.append('void')
        ctypes_sig_list.append('returning ({})'
                               .format(type_manager.get_type(function.return_type)
                                       .get_ctypes_value()))
        ctypes_sig = ' @-> '.join(ctypes_sig_list)

        returned_params = list(filter(lambda param: type_manager.get_type(
            param.arg_type).return_value('') is not None, function.parameters))
        returned_values = list(
            map(lambda param: type_manager.get_type(param.arg_type)
                .return_value(param.ocaml_name), returned_params))
        returned_types = list(map(lambda param: check_enclosing_module(
            type_manager.get_type(param.arg_type).get_ocaml_type()), returned_params))
        erase_return_unit = function.return_type == 'void' and len(
            returned_params) > 0
        if not erase_return_unit:
            returned_values.append('res')
            returned_types.append(check_enclosing_module(type_manager.get_type(
                function.return_type).get_ocaml_type()))

        is_draw_function = draw_in_out_mat_count == 1 \
            and function.return_type == 'void' \
            and len(returned_params) == 0 \
            and optional_param_count < len(floated_params) - 1

        if not mli_only:
            opencv_ml.write('let __{} = foreign "{}" ({})'
                            .format(function.ocaml_name, function.c_name, ctypes_sig))
            opencv_ml.write('let {} {} ='
                            .format(function.ocaml_name, ' '.join(floated_param_names)))
            opencv_ml.indent()
            for param in function.parameters:
                param_type = type_manager.get_type(param.arg_type)
                if param_type.is_cloneable():
                    fmt = "let {0} = if {0}_recycle then {0} else Cvdata.clone {0} in let {{}}' = {{}} in" \
                        .format(param.ocaml_name)
                else:
                    fmt = "let {}' = {} in"
                opencv_ml.write(fmt.format(param.ocaml_name, param_type
                                           .ocaml_to_ctypes(param.ocaml_name)))
            opencv_ml.write('let {} = {} in'
                            .format('_' if erase_return_unit else 'res',
                                    type_manager.get_type(function.return_type)
                                    .ctypes_to_ocaml('__{} {}'
                                                     .format(function.ocaml_name,
                                                             ' '.join(param_names_prime)))))
            for param in function.parameters:
                post_func = type_manager.get_type(param.arg_type) \
                    .ocaml_to_ctypes(param.ocaml_name).post
                if post_func is not None:
                    post = post_func(param.ocaml_name,
                                     "{}'".format(param.ocaml_name))
                    opencv_ml.write('{};'.format(post))
            opencv_ml.write(', '.join(returned_values))
            opencv_ml.unindent()

        def get_param_type(param):
            typ = type_manager.get_type(param.arg_type)
            typ_name = check_enclosing_module(typ.get_ocaml_param_type())
            if typ.has_default_value() or param.default_value is not None:
                return '?{}:{}'.format(param.ocaml_name, typ_name)
            else:
                return typ_name

        ocaml_sig_list = list(map(get_param_type, floated_params))
        if 0 < len(function.parameters) <= total_default_params:
            ocaml_sig_list.append('unit')
        if len(ocaml_sig_list) == 0:
            ocaml_sig_list.append('unit')
        ocaml_sig_list.append(' * '.join(returned_types))
        ocaml_sig = ' -> '.join(ocaml_sig_list)

        opencv_mli.write()

        opencv_mli.write('(**')
        opencv_mli.write(sanitize_docs(function.docs, name=function.ocaml_name,
                                       params=floated_params, param_map=function.param_map,
                                       extra_unit=len(function.parameters) <= total_default_params))
        opencv_mli.write('*)')

        opencv_mli.write('val {} : {}'.format(function.ocaml_name, ocaml_sig))

        if is_draw_function:
            def is_draw_function_param(param):
                return type_manager.get_type(param.arg_type).is_draw_function()
            filtered_params = list(filter(lambda x: not is_draw_function_param(x),
                                          floated_params))
            draw_function_param = list(filter(is_draw_function_param, floated_params))[0]
            draw_functions.append((function, floated_params,
                                   filtered_params, draw_function_param, enclosing_module))

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
                opencv_ml.write('include {}'.format(
                    classes[cls.inherits].ocaml_name))

                # manual include
                opencv_mli.write('type t = {}'.format(cls.ocaml_type))
                for function in classes[cls.inherits].functions:
                    write_function(
                        function, enclosing_module=cls.ocaml_name, mli_only=True)
            else:
                print('Class {} inherits from {}, but {} does not exist'.format(
                    cls.cpp_name, cls.inherits, cls.inherits))
        else:
            opencv_ml.write('type t = {}'.format(cls.ocaml_type))
            if cls.public_type:
                opencv_mli.write('type t = {}'.format(cls.ocaml_type))
            else:
                opencv_mli.write('type t')

        for function in cls.functions:
            write_function(function, enclosing_module=cls.ocaml_name)

        opencv_ml.unindent()
        opencv_ml.write('end')

        opencv_mli.unindent()
        opencv_mli.write('end')

    def write_draw_module():
        opencv_mli.write()
        opencv_mli.write('(** Allows for pure-functional drawing operations by queueing')
        opencv_mli.write('    a sequence of operations to be drawn at once on a copy of')
        opencv_mli.write('    the source image with [draw]. *)')
        opencv_mli.write('module Draw : sig')
        opencv_mli.indent()

        opencv_ml.write()
        opencv_ml.write('module Draw = struct')
        opencv_ml.indent()

        opencv_mli.write('(** A deferred drawing operation produced by the drawing')
        opencv_mli.write('    functions below and consumed by [draw]. *)')
        opencv_mli.write('type t')
        opencv_mli.write()
        opencv_mli.write('(** [draw queue mat] is the mat resulting from sequentially')
        opencv_mli.write('    performing all drawing operations in the [queue] to [mat].')
        opencv_mli.write('    The returned mat starts as a clone of [mat], so [mat] is')
        opencv_mli.write('    not modified, i.e. this is a pure function. *)')
        opencv_mli.write('val draw : t list -> Cvdata.t -> Cvdata.t')

        opencv_ml.write('type t = Cvdata.t -> unit')
        opencv_ml.write()
        opencv_ml.write('let draw lst mat =')
        opencv_ml.indent()
        opencv_ml.write('let clone = Cvdata.clone mat in')
        opencv_ml.write('List.iter (fun f -> f clone) lst;')
        opencv_ml.write('clone')
        opencv_ml.unindent()

        for function, params, filtered_params, draw_param, encl_module in draw_functions:
            def get_optioned_type(param):
                typ = type_manager.get_type(param.arg_type)
                if typ.has_default_value() or param.default_value is not None:
                    return '?{}:{}'.format(param.ocaml_name, typ.get_ocaml_param_type())
                else:
                    return typ.get_ocaml_param_type()

            sig = ' -> '.join(map(get_optioned_type, filtered_params))
            opencv_mli.write()
            opencv_mli.write('val {} : {} -> t'.format(function.ocaml_name, sig))

            def get_optioned_name(param):
                typ = type_manager.get_type(param.arg_type)
                if typ.has_default_value() or param.default_value is not None:
                    return '?{}'.format(param.ocaml_name)
                else:
                    return param.ocaml_name

            filtered_names = ' '.join(map(get_optioned_name, filtered_params))
            unfiltered_names = ' '.join(map(get_optioned_name, params))
            func_name = '{}.{}'.format(encl_module, function.ocaml_name) \
                if encl_module is not None else function.ocaml_name
            opencv_ml.write()
            opencv_ml.write('let {} {} {} ='.format(function.ocaml_name,
                                                    filtered_names, draw_param.ocaml_name))
            opencv_ml.indent()
            opencv_ml.write('{} {}'.format(func_name, unfiltered_names))
            opencv_ml.unindent()

        opencv_mli.unindent()
        opencv_mli.write('end')

        opencv_ml.unindent()
        opencv_ml.write('end')

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

    write_draw_module()

    opencv_mli.write()
    opencv_mli.write('module Cvconst : sig')
    opencv_mli.indent()

    opencv_ml.write()
    opencv_ml.write('module Cvconst = struct')
    opencv_ml.indent()

    for enum in enums:
        write_enum(enum)

    write_enum_converter()

    opencv_mli.unindent()
    opencv_mli.write('end')

    opencv_ml.unindent()
    opencv_ml.write('end')

    opencv_ml.write()
    opencv_ml.write('let (~~) = Cvconst.int_of_cv_const')
    opencv_ml.write()

    opencv_mli.write()
    opencv_mli.write('val (~~) : Cvconst.cv_const -> int')
    opencv_mli.write()

    opencv_h.unindent()
    opencv_h.write('}')

    opencv_cpp.unindent()
    opencv_cpp.write('}')

    opencv_h.save()
    opencv_cpp.save()
    opencv_ml.save()
    opencv_mli.save()

    print('Missing types:', missing_types)
