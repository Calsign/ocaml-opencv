
class Conv(str):
    def __new__(self, conv, *args, **kwargs):
        return super(Conv, self).__new__(self, conv)

    def __init__(self, conv, post=None):
        self.post = post

class Type():
    def get_cpp_type(self):
        """The type used in the original OpenCV C++ header.
        """
        raise Exception('Unimplemented')

    def get_c_type(self):
        """The type used in the generated C file.
        """
        raise Exception('Unimplemented')

    def get_ctypes_type(self):
        """The type used in OCaml ctypes types.
        """
        raise Exception('Unimplemented')

    def get_ctypes_value(self):
        """The value used in OCaml ctypes type expressions.
        """
        raise Exception('Unimplemented')

    def get_ocaml_type(self):
        """The type used in OCaml.
        """
        raise Exception('Unimplemented')

    def cpp_to_c(self, val):
        return Conv(val)

    def c_to_cpp(self, val):
        return Conv(val)

    def ctypes_to_ocaml(self, val):
        return Conv(val)

    def ocaml_to_ctypes(self, val):
        return Conv(val)

    def must_pass_pointer(self):
        """False iff this value can be passed on the stack.
        (True iff it must be passed on the heap insead.)
        """
        return False

    def is_pointer(self):
        """True iff this type is a pointer.
        """
        return False

    def has_default_value(self):
        return self.get_default_value() != None

    def get_default_value(self):
        """An OCaml string default value for arguments of this type
        iff it is optional, otherwise None.
        """
        return None

    def is_return_value(self):
        """True iff parameters of this type should be returned.
        """
        return False

    def is_cloneable(self):
        """True iff parameters of this type should be optionally cloned
        before being returned (making pure functions out of impure functions).
        """
        return False

class BaseType(Type):
    def __init__(self, cpp_type, c_type, ctypes_type, ctypes_value, ocaml_type):
        self.cpp_type = cpp_type
        self.c_type = c_type
        self.ctypes_type = ctypes_type
        self.ctypes_value = ctypes_value
        self.ocaml_type = ocaml_type

    def get_cpp_type(self):
        return self.cpp_type

    def get_c_type(self):
        return self.c_type

    def get_ctypes_type(self):
        return self.ctypes_type

    def get_ctypes_value(self):
        return self.ctypes_value

    def get_ocaml_type(self):
        return self.ocaml_type

class String(BaseType):
    def __init__(self):
        super().__init__('cv::String', 'const char *', 'string', 'string', 'string')

    def cpp_to_c(self, val):
        return Conv('({}).c_str()'.format(val))

    def c_to_cpp(self, val):
        return Conv('cv::String({})'.format(val))

class WrapperType(Type):
    def __init__(self, inner):
        self.inner = inner

    def get_cpp_type(self):
        return self.inner.get_cpp_type()

    def get_c_type(self):
        return self.inner.get_c_type()

    def get_ctypes_type(self):
        return self.inner.get_ctypes_type()

    def get_ctypes_value(self):
        return self.inner.get_ctypes_value()

    def get_ocaml_type(self):
        return self.inner.get_ocaml_type()

    def cpp_to_c(self, val):
        return self.inner.cpp_to_c(val)

    def c_to_cpp(self, val):
        return self.inner.c_to_cpp(val)

    def ctypes_to_ocaml(self, val):
        return self.inner.ctypes_to_ocaml(val)

    def ocaml_to_ctypes(self, val):
        return self.inner.ocaml_to_ctypes(val)

class Const(WrapperType):
    def __init__(self, inner):
        super().__init__(inner)

    def get_cpp_type(self):
        # don't double const
        return 'const {}'.format(self.inner.get_cpp_type().replace('const ', ''))

    def get_c_type(self):
        # don't double const
        return 'const {}'.format(self.inner.get_c_type().replace('const ', ''))

class GenericPointer(WrapperType):
    def __init__(self, inner, pointer_char):
        super().__init__(inner)
        self.pointer_char = pointer_char

    def get_cpp_type(self):
        return '{}{}'.format(self.inner.get_cpp_type(), self.pointer_char)

    def get_c_type(self):
        return '{}{}'.format(self.inner.get_c_type(), self.pointer_char)

    def get_ctypes_type(self):
        return '({}) ptr'.format(self.inner.get_ctypes_type())

    def get_ctypes_value(self):
        return 'ptr ({})'.format(self.inner.get_ctypes_value())

    def get_ocaml_type(self):
        return self.inner.get_ocaml_type()

    def ctypes_to_ocaml(self, val):
        return Conv(self.inner.ctypes_to_ocaml('(!@ ({}))'.format(val)))

    def ocaml_to_ctypes(self, val):
        return Conv('(allocate ({}) ({}))'.format(self.inner.get_ctypes_value(),
                                                  self.inner.ocaml_to_ctypes(val)))

    def is_pointer(self):
        return True

class Pointer(GenericPointer):
    def __init__(self, inner):
        super().__init__(inner, '*')

class Reference(GenericPointer):
    def __init__(self, inner):
        super().__init__(inner, '&')

class Array(WrapperType):
    def __init__(self, inner, dimension=None):
        super().__init__(inner)
        self.dimension = dimension

    def get_dimension_str(self):
        return '' if self.dimension is None else str(self.dimension)

    def get_cpp_type(self):
        return '{}[{}]'.format(self.inner.get_cpp_type(),
                               self.get_dimension_str())

    def get_c_type(self):
        return '{}[{}]'.format(self.inner.get_c_type(),
                               self.get_dimension_str())

    def get_ctypes_type(self):
        return '({}) ptr'.format(self.get_ctypes_type())

    def get_ctypes_value(self):
        return 'ptr ({})'.format(self.get_ctypes_value())

    def get_ocaml_type(self):
        # TODO currently no fancy processing to extract array values
        return '({}) ptr'.format(self.inner.get_ctypes_type())

class Vector(WrapperType):
    def __init__(self, inner):
        super().__init__(inner)

    def get_cpp_type(self):
        return 'std::vector<{}>'.format(self.inner.get_cpp_type())

    def get_c_type(self):
        return 'std::vector<{}>'.format(self.inner.get_c_type())

    def get_ctypes_type(self):
        return '({}) ptr'.format(self.inner.get_ctypes_type())

    def get_ctypes_value(self):
        return 'ptr ({})'.format(self.inner.get_ctypes_value())

    def get_ocaml_type(self):
        return '({}) list'.format(self.inner.get_ocaml_type())

    def ctypes_to_ocaml(self, val):
        return Conv('list_of_vector ({}) ({}) |> List.map (fun x -> {})'
                    .format(self.inner.get_ctypes_value(), val,
                            self.inner.ctypes_to_ocaml('x')))

    def ocaml_to_ctypes(self, val):
        # TODO what if the std::vector is also an output?
        # i.e. do we need to do the same kind of backpatching that we do for Mat?
        return Conv('vector_of_list ({}) ({} |> List.map (fun x -> {})) |> from_voidp ({})'
                    .format(self.inner.get_ctypes_value(), val,
                            self.inner.ocaml_to_ctypes('x'),
                            self.inner.get_ctypes_value()))

    def must_pass_pointer(self):
        return True

class CustomType(BaseType):
    def __init__(self, cpp_type, c_type, ctypes_type, ctypes_value, ocaml_type,
                 cpp2c='{}', c2cpp='{}', ctypes2ocaml='{}', ocaml2ctypes='{}', post=None,
                 must_pointerize=False):

        super().__init__(cpp_type, c_type, ctypes_type, ctypes_value, ocaml_type)
        self.cpp2c = cpp2c
        self.c2cpp = c2cpp
        self.ctypes2ocaml = ctypes2ocaml
        self.ocaml2ctypes = ocaml2ctypes
        self.post = post
        self.must_pointerize = must_pointerize

    def cpp_to_c(self, val):
        return Conv(self.cpp2c.format(val))

    def c_to_cpp(self, val):
        return Conv(self.c2cpp.format(val))

    def ctypes_to_ocaml(self, val):
        return Conv(self.ctypes2ocaml.format(val))

    def ocaml_to_ctypes(self, val):
        post = None if self.post is None else self.post.format(val)
        return Conv(self.ocaml2ctypes.format(val), post=post)

    def must_pass_pointer(self):
        return self.must_pointerize

class Mat(Type):
    def get_cpp_type(self):
        return 'cv::Mat'

    def get_c_type(self):
        return 'cv::Mat'

    def get_ctypes_type(self):
        return 'unit ptr'

    def get_ctypes_value(self):
        return 'ptr void'

    def get_ocaml_type(self):
        return 'Mat.t'

    def ctypes_to_ocaml(self, val):
        return Conv('(Mat.bigarray_of_cmat ({}))'.format(val))

    def _post(self, original, converted):
        return 'Mat.copy_cmat_bigarray {} {}'.format(original, converted)

    def ocaml_to_ctypes(self, val):
        return Conv('(Mat.cmat_of_bigarray ({}))'.format(val), post=self._post)

    def must_pass_pointer(self):
        return True

class Cvdata(Type):
    def __init__(self, cpp_type, optional=False, ret=False, cloneable=False):
        self.cpp_type = cpp_type
        self.optional = optional
        self.ret = ret
        self.cloneable = cloneable

    def get_cpp_type(self):
        return 'cv::{}'.format(self.cpp_type)

    def get_c_type(self):
        return 'cv::{}'.format(self.cpp_type)

    def get_ctypes_type(self):
        return 'unit ptr'

    def get_ctypes_value(self):
        return 'ptr void'

    def get_ocaml_type(self):
        return 'Cvdata.t'

    def ctypes_to_ocaml(self, val):
        return Conv('(Cvdata.extract_cvdata ({}))'.format(val))

    def _post(self, original, converted):
        return 'Cvdata.pack_cvdata_post {} {}'.format(original, converted)

    def ocaml_to_ctypes(self, val):
        return Conv('(Cvdata.pack_cvdata ({}))'.format(val), post=self._post)

    def get_default_value(self):
        return '(Cvdata.Mat (Mat.create ()))' if self.optional else None

    def is_return_value(self):
        return self.ret

    def is_cloneable(self):
        return self.cloneable

class Scalar(Type):
    def get_cpp_type(self):
        return 'cv::Scalar'

    def get_c_type(self):
        return 'cv::Scalar *'

    def get_ctypes_type(self):
        return 'unit ptr'

    def get_ctypes_value(self):
        return 'ptr void'

    def get_ocaml_type(self):
        return 'Scalar.t'

    def c_to_cpp(self, val):
        return Conv('*({})'.format(val))

    def ctypes_to_ocaml(self, val):
        return Conv('(Scalar.ctypes_to_ocaml ({}))'.format(val))

    def ocaml_to_ctypes(self, val):
        return Conv('(Scalar.ocaml_to_ctypes ({}))'.format(val))

    def must_pass_pointer(self):
        return True

class RecycleFlag(BaseType):
    def __init__(self):
        super().__init__('__recycle_flag', 'bool', 'bool', 'bool', 'bool')

    def get_default_value(self):
        return 'false'

CONST = 'const'
STD_VECTOR = 'std::vector<'
CV_NAMESPACE = 'cv::'

type_map = {}

def add_type(new_type, silent_on_exists=False):
    if new_type.get_cpp_type() in type_map:
        if not silent_on_exists:
            raise Exception('Trying to add previously added type: {}'
                            .format(new_type.get_cpp_type()))
    else:
        type_map[new_type.get_cpp_type()] = new_type

def wrap_type(cls, inner, *args):
    return None if inner is None else cls(inner, *args)

def get_type(cpp_name):
    """Returns the type associated with the given C++ name.
    Returns None if no type could be found.
    """
    cpp_name = cpp_name.strip()
    if cpp_name in type_map:
        return type_map[cpp_name]
    if (CV_NAMESPACE + cpp_name) in type_map:
        return type_map[CV_NAMESPACE + cpp_name]
    if cpp_name.startswith(CONST):
        return wrap_type(Const, get_type(cpp_name[len(CONST):]))
    if cpp_name.endswith('*'):
        return wrap_type(Pointer, get_type(cpp_name[:-1]))
    if cpp_name.endswith('&'):
        return wrap_type(Reference, get_type(cpp_name[:-1]))
    if cpp_name.endswith(']'):
        try:
            left = cpp_name.rindex('[')
            return wrap_type(Array, get_type(cpp_name[:left]), cpp_name[left+1:-1])
        except ValueError:
            pass
    if cpp_name.startswith(STD_VECTOR):
        try:
            right = cpp_name.rindex('>')
            return wrap_type(Vector, get_type(cpp_name[len(STD_VECTOR):right]))
        except ValueError:
            pass
    print('Could not find type for cpp_name: {}'.format(cpp_name))
    return None

def has_type(cpp_name):
    return get_type(cpp_name) is not None

def add_type_alias(type_name, alias):
    existing_type = get_type(type_name)
    assert existing_type is not None
    assert alias not in type_map
    type_map[alias] = existing_type

def add_types():
    add_type(BaseType('void', 'void', 'unit', 'void', 'unit'))
    add_type(BaseType('int', 'int', 'int', 'int', 'int'))
    add_type(BaseType('double', 'double', 'float', 'double', 'float'))
    add_type(BaseType('float', 'float', 'float', 'float', 'float'))
    add_type(BaseType('bool', 'bool', 'bool', 'bool', 'bool'))
    add_type(BaseType('char', 'char', 'char', 'char', 'char'))
    add_type(String())

    add_type(Mat())
    add_type(Scalar())

    add_type(Cvdata('InputArray'))
    add_type(Cvdata('OutputArray', optional=True, ret=True))
    add_type(Cvdata('InputOutputArray', ret=True, cloneable=True))
    add_type(Cvdata('InputArrayOfArrays'))
    add_type(Cvdata('OutputArrayOfArrays', optional=True, ret=True))
    add_type(Cvdata('InputOutputArrayOfArrays', ret=True, cloneable=True))

    add_type(RecycleFlag())

add_types()
