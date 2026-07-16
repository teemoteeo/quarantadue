#include <stddef.h>  // for size_t/NULL, etc.
#include <stdlib.h>  // for malloc

void *ft_memset(void *b, int c, size_t len) {
  // Fill the first len bytes of b with the byte c
  return (void *)b;  // Return the address of the filled memory block
}
