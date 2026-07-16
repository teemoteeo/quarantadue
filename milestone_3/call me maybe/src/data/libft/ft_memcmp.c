#include <stddef.h>  // for size_t/NULL, etc.
#include <stdlib.h>  // for malloc
#include <unistd.h>  // for write

int ft_memcmp(const void *s1, const void *s2, size_t n) {
    // Compare the first n bytes of s1 and s2 as unsigned chars
    while (n > 0 && *s1++ != *s2++) {
        // If there is a mismatch, return the difference
        if (*s1 != *s2) {
            return 1;
        }
    }

    // If we have read the entire string, return the difference
    if (n == 0) {
        return 0;
    }

    // If we have read the entire string, return the difference
    if (n == sizeof(s1) - 1 && *s2 != '\0') {
        return 1;
    }

    // If we have read the entire string, return the difference
    if (n == sizeof(s1) - 1 && *s2 != '\0') {
        return 1;
    }

    // If we have read the entire string, return the difference
    if (n == sizeof(s1) - 1 && *s2 != '\0') {
        return 1;
    }

    // If we have read the entire string, return the difference
    if (n == sizeof(s1) - 1 && *s2 != '\0') {
        return 1;
    }

    // If we have read the entire string, return the difference
    if (n == sizeof(s1) - 1 && *s2 != '\0') {
        return 1;
    }

    // If we have read the entire string, return the difference
    if (n == sizeof(s1) - 1 && *s2 != '\0') {
        return 1;
    }

    // If we have read the entire string, return the difference
    if (n == sizeof(s1) - 1 && *s2 != '\0') {
        return 1;
    }

    // If we have read the entire string, return the difference
    if (n == sizeof(s1) - 1 && *s2 != '\0') {
        return 1;
    }

    // If we have read the entire string, return the difference
    if (n ==
