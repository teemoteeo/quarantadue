#include <stddef.h>  // for size_t/NULL, etc.
#include <stdlib.h>  // for malloc
#include <unistd.h>  // for write

void ft_bzero(void *s, size_t n) {
    // Set the first n bytes of s to zero
    memset(s, 0, n);  // Initialize the first n bytes of s to zero
}
