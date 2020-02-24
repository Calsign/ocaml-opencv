
#include <stdlib.h>
#include <opencv2/opencv.hpp>
#include <caml/mlvalues.h>
#include <caml/bigarray.h>
#include <caml/fail.h>

extern "C" {
    cv::Mat *create_mat();
    void mat_copy(cv::Mat *src, cv::Mat *dst);

    typedef struct caml_ba_array bigarray;

    int mat_num_dims(cv::Mat *mat);
    int *mat_dims(cv::Mat *mat);
    uchar *mat_data(cv::Mat *mat);

    cv::Mat *mat_of_bigarray(int num_dims, int *dims, char *data);

    void copy_mat_bigarray(cv::Mat *mat, value *v);

    cv::Mat *mat_of_inputarray(cv::InputArray arr);
    std::vector<cv::Mat> *mat_vector_of_inputarray(cv::InputArray arr);

    void *vector_data(std::vector<char> v);
    int vector_length(std::vector<char> v);

    std::vector<char> *create_vector(char &arr, int length, int item_size);

    bool is_mat(cv::InputArray cvdata);
    bool is_vector_mat(cv::InputArray cvdata);
    bool is_vector_bool(cv::InputArray cvdata);

    cv::InputArray inputarray_of_mat(const cv::Mat &mat);
    cv::InputArray inputarray_of_mat_vector(const std::vector<cv::Mat> &mats);

    cv::Scalar *build_scalar(double w, double x, double y, double z);
    double scalar_w(cv::Scalar &scalar);
    double scalar_x(cv::Scalar &scalar);
    double scalar_y(cv::Scalar &scalar);
    double scalar_z(cv::Scalar &scalar);
}
