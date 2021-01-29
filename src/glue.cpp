
#include "glue.h"
#include <stdio.h>

extern "C" {
    // Mat functions

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

    void mat_copy(cv::Mat *src, cv::Mat *dst) {
        src->copyTo(*dst);
    }

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


    // Vector functions

    void *vector_data(std::vector<char> v) {
        return v.data();
    }

    int vector_length(std::vector<char> v) {
        return v.size();
    }

    std::vector<char> *create_vector(char &arr, int length, int item_size) {
        return new std::vector<char>(length * item_size, arr);
    }


    // InputArray functions

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

    int inputarray_array_length(cv::InputArrayOfArrays arr) {
        if (!arr.isMatVector()) {
            caml_failwith("opencv: InputArray is not vector of Mat");
        }
        return arr.size().area();
    }

    cv::Mat *mat_from_inputarray_array(cv::InputArrayOfArrays arr, int index) {
        if (!arr.isMatVector()) {
            caml_failwith("opencv: InputArray is not vector of Mat");
        }
        cv::Mat *mat = new cv::Mat(arr.getMat(index));
        return mat;
    }

    int inputarray_kind(cv::InputArray cvdata) {
        switch (cvdata.kind()) {
        case cv::_InputArray::NONE:
            return 0;
        case cv::_InputArray::MAT:
            return 1;
        case cv::_InputArray::MATX:
            return 2;
        case cv::_InputArray::STD_VECTOR:
            return 3;
        case cv::_InputArray::STD_VECTOR_VECTOR:
            return 4;
        case cv::_InputArray::STD_VECTOR_MAT:
            return 5;
        case cv::_InputArray::EXPR:
            return 6;
        case cv::_InputArray::OPENGL_BUFFER:
            return 7;
        case cv::_InputArray::CUDA_HOST_MEM:
            return 8;
        case cv::_InputArray::CUDA_GPU_MAT:
            return 9;
        case cv::_InputArray::UMAT:
            return 10;
        case cv::_InputArray::STD_VECTOR_UMAT:
            return 11;
        case cv::_InputArray::STD_BOOL_VECTOR:
            return 12;
        case cv::_InputArray::STD_VECTOR_CUDA_GPU_MAT:
            return 13;
        case cv::_InputArray::STD_ARRAY:
            return 14;
        case cv::_InputArray::STD_ARRAY_MAT:
            return 15;
        default:
            return -1;
        }
    }

    int mat_depth(cv::Mat *mat) {
        switch (mat->depth()) {
        case CV_8U:
            return 0;
        case CV_8S:
            return 1;
        case CV_16U:
            return 2;
        case CV_16S:
            return 3;
        case CV_32S:
            return 4;
        case CV_32F:
            return 5;
        case CV_64F:
            return 6;
        default:
            return -1;
        }
    }

    std::vector<cv::Mat> *create_vector_mat(long int length) {
        std::vector<cv::Mat> *vec = new std::vector<cv::Mat>();
        vec->reserve(length);
        return vec;
    }

    void add_vector_mat(std::vector<cv::Mat> *vec, cv::Mat &mat) {
        vec->push_back(mat);
    }

    cv::InputArray inputarray_of_mat(const cv::Mat &mat) {
        const cv::_InputArray *arr = new cv::_InputArray(mat);
        return *arr;
    }

    cv::InputArray inputarray_of_mat_vector(const std::vector<cv::Mat> &mats) {
        const cv::_InputArray *arr = new cv::_InputArray(mats);
        return *arr;
    }


    // Scalar functions

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
