#include <stddef.h>
#include <stdlib.h>

char **ft_split(char const *s, char c) {
    size_t len = 0;
    char **split = NULL;

    while ((len = strlen(s)) > 0) {
        if (s[len] == c || s[len] == '\0') {
            char *new_str = (char *)malloc(len + 1);
            if (!new_str) {
                return NULL; // Allocate memory failure
            }
            strncpy(new_str, s, len);
            new_str[len] = '\0';
            split = (char **)malloc(sizeof(char *) * len);
            if (!split) {
                free(new_str);
                return NULL; // Allocate memory failure
            }
            split[len] = new_str;
        } else {
            free(new_str);
            return NULL; // Allocate memory failure
        }
    }

    return split;
}
