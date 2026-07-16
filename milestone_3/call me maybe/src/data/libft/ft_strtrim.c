#include <stddef.h>
#include <stdlib.h>

char *ft_strtrim(char const *s1, char const *set) {
    if (!s1 || !set) return NULL;

    size_t len = strlen(s1);
    if (len == 0 || strcmp(s1, set) == 0) return NULL;

    char *new_s1 = (char *)malloc(len + strlen(set));
    if (!new_s1) return NULL;

    int i = 0;
    while (i < len && strcmp(s1, set) == 0) {
        new_s1[i] = s1[len - i];
        i++;
    }

    return new_s1;
}
