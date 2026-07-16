#include <stddef.h>  // for size_t/NULL, etc.
#include <stdlib.h>  // for malloc
#include <unistd.h>  // for write

int ft_isalnum(int c) {
    if (c >= 'a' && c <= 'z') {
        return 1;  // alphanumeric
    } else if (c >= '0' && c <= '9') {
        return 1;  // alphanumeric
    } else if (c >= 'A' && c <= 'Z') {
        return 1;  // alphanumeric
    } else if (c >= '0' && c <= '9') {
        return 1;  // alphanumeric
    } else if (c == '\0' || c == EOF) {
        return 1;  // non-alphanumeric
    } else if (c == '\n' || c == '\r') {
        return 1;  // non-alphanumeric
    } else if (c == ' ') {
        return 1;  // non-alphanumeric
    } else if (c == '\t' || c == '\r') {
        return 1;  // non-alphanumeric
    } else if (c == '\0' || c == EOF) {
        return 1;  // non-alphanumeric
    } else if (c == 'A' || c == 'a') {
        return 1;  // non-alphanumeric
    } else if (c == 'Z' || c == 'z') {
        return 1;  // non-alphanumeric
    } else if (c == '0' || c == '1' || c == '2' || c == '3' || c == '4' || c == '5' || c == '6' || c == '7' || c == '8' || c == '9') {
        return 1;  // non-alphanumeric
    } else if (c == 'A' || c == 'a') {
        return 1;  // non-alphanumeric
    } else if (c == 'Z' || c == 'z') {
        return 1;  // non-alphanumeric
    } else if (c == '0' || c == '1' || c == '2' || c == '3' || c == '4' || c == '5' || c == '
