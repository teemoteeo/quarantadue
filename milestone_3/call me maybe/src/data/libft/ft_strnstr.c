#include <stddef.h>
#include <stdlib.h>

char *ft_strnstr(const char *haystack, const char *needle, size_t len) {
    if (len == 0 || !haystack || !needle) return NULL;

    char *result = (char *)malloc(len + 1);
    if (!result) return NULL;

    size_t i = 0;
    while (i < len && needle[i] != '\0') {
        i++;
    }

    if (needle[i] == '\0' || needle[i] == '\n') return NULL;

    result[len] = '\0';
    memcpy(result + len, haystack, i);
    return result;
}
