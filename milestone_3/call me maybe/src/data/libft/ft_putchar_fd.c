#include <stddef.h>  // for size_t/NULL, etc.
#include <stdlib.h>  // for malloc
#include <unistd.h>  // for write

void ft_putchar_fd(char c, int fd) {
    if (fd < 0 || fd >= write) {
        perror("write");
        exit(EXIT_FAILURE);
    }
    write(fd, &c, 1);  // Write single character to the file descriptor
}
