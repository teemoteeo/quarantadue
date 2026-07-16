#include <stddef.h>  // for size_t, NULL

char *ft_substr(char const *s, unsigned int start, size_t len) {
  if (start > strlen(s)) {
    return NULL;  // allocation failure
  }
  char *substr = (char *)malloc(len + 1);  // allocate memory for the substring
  if (!substr) {
    return NULL;  // allocation failure
  }
  strncpy(substr, s + start, len);  // copy substring into the allocated memory
  return substr;
}
