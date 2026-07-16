#include <stddef.h>  // for size_t/NULL, malloc is required

char *ft_strjoin(char const *s1, char const *s2) {
    if (!s1 || !s2) return NULL;  // check for null pointer

    char *result = (char *)malloc(strlen(s1) + strlen(s2) + 1);  // allocate memory for result
    if (!result) return NULL;  // allocation failure

    strcpy(result, s1);  // copy string from s1 to result
    strcat(result, s2);  // concatenate string from s2 to result

    return result;  // return the newly allocated string
}
