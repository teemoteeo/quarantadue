#include <stddef.h>

void *ft_memcpy(void *dst, const void *src, size_t n) {
    // Copy n bytes from src to dst (areas must not overlap)
    while(n--) *dst = *src;
    return dst;
}
