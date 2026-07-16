#include <stddef.h>  // for size_t, NULL, and strlen

char *ft_strrchr(const char *s, int c) {
  if (s == NULL || s == '\0') {
    return NULL;  // string is null or at the end of the string
  }
  char *ptr = (char *)s - 1;  // calculate the position of c in s
  while (ptr > s && c != '\0') {
    ptr--;
    c++;
  }
  return (char *)s;  // return the pointer to the last occurrence of c
}
