
#include <stdlib.h>
#include <opencv2/opencv.hpp>
#include <caml/mlvalues.h>
#include <caml/bigarray.h>
#include <caml/fail.h>

extern "C" {
    // Mat functions

    cv::Mat *create_mat();
    void mat_copy(cv::Mat *src, cv::Mat *dst);

    typedef struct caml_ba_array bigarray;

    int mat_num_dims(cv::Mat *mat);
    int *mat_dims(cv::Mat *mat);
    uchar *mat_data(cv::Mat *mat);

    cv::Mat *mat_of_bigarray(int num_dims, int *dims, char *data);
    void copy_mat_bigarray(cv::Mat *mat, value *v);


    // Vector functions

    void *vector_data(std::vector<char> v);
    int vector_length(std::vector<char> v);
    std::vector<char> *create_vector(char &arr, int length, int item_size);


    // InputArray functions

    cv::Mat *mat_of_inputarray(cv::InputArray arr);
    std::vector<cv::Mat> *mat_vector_of_inputarray(cv::InputArray arr);
    int inputarray_array_length(cv::InputArrayOfArrays arr);
    cv::Mat *mat_from_inputarray_array(cv::InputArrayOfArrays arr, int index);

    int inputarray_kind(cv::InputArray cvdata);
    int mat_depth(cv::Mat *mat);

    std::vector<cv::Mat> *create_vector_mat(long int length);
    void add_vector_mat(std::vector<cv::Mat> *vec, cv::Mat &mat);

    cv::InputArray inputarray_of_mat(const cv::Mat &mat);
    cv::InputArray inputarray_of_mat_vector(const std::vector<cv::Mat> &mats);


    // Scalar functions

    cv::Scalar *build_scalar(double w, double x, double y, double z);
    double scalar_w(cv::Scalar &scalar);
    double scalar_x(cv::Scalar &scalar);
    double scalar_y(cv::Scalar &scalar);
    double scalar_z(cv::Scalar &scalar);
}
