
#include "glue.h"
#include <stdio.h>

extern "C" {
    cv::Mat *create_mat() {
        // We need to initialize the mat with at least 2 dimensions.
        // If we don't, there will be significant issues because
        // OCaml Bigarrays increase the number of dimensions, as this
        // would require allocating more memory.
        // Perhaps a solution is initialize all Bigarrays with the
        // maximum number of dimensions (16) and waste a little bit
        // of space but never run into issues like this.
        // Note that the current solution, i.e. initializing mats with
        // two dimensions, works for all images.
        return new cv::Mat(0, 0, CV_8UC3);
    }

    // cv::Mat *mat_of_bigarray(bigarray *arr) {
    //     // The last dimension is for different channels.
    //     // OpenCV treats this separately from other dimensions,
    //     // but OCaml's Bigarray treats them just like other dimensions.
    //     int ndims = arr->num_dims - 1;
    //     int *dims = new int[ndims];
    //     for (int i = 0; i < ndims; i++) {
    //         dims[i] = arr->dim[i];
    //     }
    //     int channels = arr->dim[ndims];
    //     int type = CV_MAKETYPE(CV_8U, channels);
    //     void *data = arr->data;

    //     return new cv::Mat(ndims, dims, type, data);
    // }

    // void copy_mat_to_bigarray(cv::Mat *mat, bigarray *arr) {
    //     arr->flags = CAML_BA_EXTERNAL + CAML_BA_C_LAYOUT + CAML_BA_UINT8;
    //     arr->data = mat->data;

    //     if (mat->size.dims() + 1 > arr->num_dims) {
    //         // Uh-oh TODO throw exception
    //         // We can't re-allocate the bigarray so we're kind of screwed
    //     }
    //     for (int i = 0; i < mat->size.dims(); i++) {
    //         arr->dim[i] = mat->size[i];
    //     }
    //     arr->num_dims = mat->size.dims() + 1;
    //     arr->dim[mat->size.dims()] = mat->channels();
    // }

    // value bigarray_of_mat(cv::Mat *mat) {
    //     //bigarray *arr = new bigarray;
    //     //copy_mat_to_bigarray(mat, arr);

    //     //intnat flags = CAML_BA_EXTERNAL + CAML_BA_C_LAYOUT + CAML_BA_UINT8;
    //     int flags = CAML_BA_C_LAYOUT | CAML_BA_UINT8;
    //     void *data = mat->data;
    //     intnat num_dims = mat->size.dims() + 1;
    //     intnat *dim = new intnat[num_dims];
    //     for (int i = 0; i < mat->size.dims(); i++) {
    //         dim[i] = mat->size[i];
    //     }
    //     dim[mat->size.dims()] = mat->channels();

    //     printf("dims: %i\n", (int) num_dims);

    //     return caml_ba_alloc(flags, num_dims, data, dim);
    // }

    int mat_num_dims(cv::Mat *mat) {
        return mat->size.dims() + 1;
    }

    int *mat_dims(cv::Mat *mat) {
        int *dim = new int[mat->size.dims() + 1];
        for (int i = 0; i < mat->size.dims(); i++) {
            dim[i] = mat->size[i];
        }
        dim[mat->size.dims()] = mat->channels();
        return dim;
    }

    uchar *mat_data(cv::Mat *mat) {
        return mat->data;
    }

    cv::Mat *mat_of_bigarray(int num_dims, int *dims, char *data) {
        int ndims = num_dims - 1;
        int channels = dims[ndims];
        int type = CV_MAKETYPE(CV_8U, channels);
        return new cv::Mat(ndims, dims, type, data);
    }

    void copy_mat_bigarray(cv::Mat *mat, value *v) {
        bigarray *ba = Caml_ba_array_val(*v);
        if (mat->size.dims() + 1 > ba->num_dims) {
            // TODO this is a problem
            // Need to throw an exception or something
            caml_failwith("opencv: mat increased dimensionality");
        }
        ba->data = mat->data;
        ba->num_dims = mat->size.dims() + 1;
        for (int i = 0; i < mat->size.dims(); i++) {
            ba->dim[i] = mat->size[i];
        }
        ba->dim[mat->size.dims()] = mat->channels();
    }

    cv::Mat *mat_of_inputarray(cv::InputArray arr) {
        if (!arr.isMat()) {
            caml_failwith("opencv: InputArray is not Mat");
        }
        cv::Mat *mat = new cv::Mat(arr.getMat());
        return mat;
    }

    std::vector<cv::Mat> *mat_vector_of_inputarray(cv::InputArray arr) {
        if (!arr.isMatVector()) {
            caml_failwith("opencv: InputArray is not vector<Mat>");
        }
        std::vector<cv::Mat> vector;
        arr.getMatVector(vector);
        return new std::vector<cv::Mat>(vector);
    }

    void *vector_data(std::vector<char> v) {
        return v.data();
    }

    int vector_length(std::vector<char> v) {
        return v.size();
    }

    std::vector<char> *create_vector(char &arr, int length, int item_size) {
        return new std::vector<char>(length * item_size, arr);
    }

    bool is_mat(cv::InputArray cvdata) {
        return cvdata.kind() == cv::_InputArray::MAT;
    }
    bool is_vector_mat(cv::InputArray cvdata) {
        return cvdata.kind() == cv::_InputArray::STD_VECTOR_MAT;
    }
    bool is_vector_bool(cv::InputArray cvdata) {
        return cvdata.kind() == cv::_InputArray::STD_BOOL_VECTOR;
    }

    cv::InputArray inputarray_of_mat(const cv::Mat &mat) {
        const cv::_InputArray *arr = new cv::_InputArray(mat);
        return *arr;
    }
    cv::InputArray inputarray_of_mat_vector(const std::vector<cv::Mat> &mats) {
        const cv::_InputArray *arr = new cv::_InputArray(mats);
        return *arr;
    }

    cv::Scalar *build_scalar(double w, double x, double y, double z) {
        return new cv::Scalar(w, x, y, z);
    }

    double scalar_w(cv::Scalar &scalar) {
        return scalar[0];
    }
    double scalar_x(cv::Scalar &scalar) {
        return scalar[1];
    }
    double scalar_y(cv::Scalar &scalar) {
        return scalar[2];
    }
    double scalar_z(cv::Scalar &scalar) {
        return scalar[3];
    }
}
