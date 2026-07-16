#include <stddef.h>
#include <stdlib.h>
#include <unistd.h>

void ft_putnbr_fd(int n, int fd)
{
    // Write the integer n to the file descriptor fd (handle INT_MIN).
    write(fd, &n, sizeof(int));
}
