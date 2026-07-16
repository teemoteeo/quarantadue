#include <stddef.h>  // for size_t/NULL, etc.
#include <stdlib.h>  // for malloc
#include <unistd.h>  // for write

int ft_isalpha(int c) {
    if (c >= 'a' && c <= 'z') {
        return 1;  // c is an alphabetic character
    } else if (c >= 'A' && c <= 'Z') {
        return 1;  // c is an alphabetic character
    } else if (c >= '0' && c <= '9') {
        return 1;  // c is an alphabetic character
    } else {
        return 0;  // c is not a letter
    }
}
