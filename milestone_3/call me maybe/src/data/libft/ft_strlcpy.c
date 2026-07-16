#include <stddef.h>  // for size_t/NULL, etc.
#include <stdlib.h>  // for malloc
#include <unistd.h>  // for write

size_t ft_strlcpy(char *dst, const char *src, size_t dstsize) {
    // Copy up to dstsize-1 chars from src to dst, NUL-terminate when dstsize > 0;
    // Return the length of src.
    return (size_t) write(dst, src, dstsize - 1);
}
