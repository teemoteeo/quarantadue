#include <stddef.h>
#include <stdlib.h>
#include <unistd.h>

void ft_putstr_fd(char *s, int fd) {
  write(fd, s, strlen(s));
}
