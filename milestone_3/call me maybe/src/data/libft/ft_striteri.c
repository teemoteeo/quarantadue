#include <stddef.h>

void ft_striteri(char *s, void (*f)(unsigned int, char *)) {
  unsigned int i;
  for (i = 0; s[i] != '\0'; i++) {
    f(i, s[i]);
  }
}
