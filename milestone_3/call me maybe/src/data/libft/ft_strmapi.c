#include <stddef.h>  // for size_t/NULL, malloc is required

char *ft_strmapi(char const *s, char (*f)(unsigned int, char)) {
    if (!s || !f) return NULL;  // check for null pointers and invalid functions

    char *new_str = (char *)malloc(sizeof(char) * strlen(s));  // allocate memory for the new string
    if (!new_str) return NULL;  // allocation failed

    for (unsigned int i = 0; i < strlen(s); ++i) {
        new_str[i] = f(i, s[i]);  // apply the function to each character
    }

    return new_str;  // return the newly allocated string
}
