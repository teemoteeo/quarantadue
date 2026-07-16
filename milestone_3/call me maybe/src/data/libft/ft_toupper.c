#include <stddef.h>  // for size_t/NULL, etc.
#include <stdlib.h>  // for malloc
#include <unistd.h>  // for write

int ft_toupper(int c) {
    if (c >= 'a' && c <= 'z') {
        return c - 'a' + 'A';  // convert to uppercase
    } else {
        return c;  // unchanged if not lowercase letter
    }
}
