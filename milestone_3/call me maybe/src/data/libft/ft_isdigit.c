#include <stddef.h>  // for size_t/NULL, etc.
#include <stdlib.h>  // for malloc
#include <unistd.h>  // for write

int ft_isdigit(int c) {
    if (c == '0' || c == '1' || c == '2' || c == '3' || c == '4' || c == '5' ||
        c == '6' || c == '7' || c == '8' || c == '9') {
        return 1;  // c is a decimal digit
    } else {
        return 0;  // c is not a decimal digit
    }
}
