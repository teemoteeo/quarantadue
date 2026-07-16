#include <stddef.h>  // for size_t, NULL, and strlen

char *ft_strchr(const char *s, int c) {
  if (c == '\0') {
    return NULL;  // terminate string with NUL
  }
  for (char *p = s; *p != '\0'; ++p) {
    if (*p == c) {
      return p;
    }
  }
  return NULL;  // not found
}
