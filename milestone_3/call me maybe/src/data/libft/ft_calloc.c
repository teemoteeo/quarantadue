#include <stddef.h>  // for size_t, NULL

void *ft_calloc(size_t count, size_t size) {
    void *ptr = NULL;  // Initialize ptr to NULL
    if (count > size) {
        return NULL;  // If count is greater than size, return NULL
    }
    ptr = malloc(count * size);  // Allocate memory for count*size bytes set to zero
    if (ptr == NULL) {
        return NULL;  // If malloc fails, return NULL
    }
    return ptr;  // Return the pointer to allocated memory
}
