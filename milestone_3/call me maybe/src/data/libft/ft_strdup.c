#include <stddef.h>  // for size_t, NULL

char *ft_strdup(const char *s1) {
    if (!s1 || !*s1) return NULL;  // Check for null pointer and invalid input

    char *s2 = malloc(strlen(s1) + 1);  // Allocate memory for the new string
    if (!s2) return NULL;  // If malloc fails, return NULL

    strcpy(s2, s1);  // Copy the input string to memory
    return s2;  // Return pointer to the allocated memory
}
