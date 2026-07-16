#include <stddef.h>  // for size_t/NULL, etc.
#include <stdlib.h>  // for malloc
#include <unistd.h>  // for write

int ft_atoi(const char *str) {
    int i = 0;
    while (str[i] == ' ') {  // skip whitespace
        i++;
    }
    int j = 0;
    while (str[i] >= '0' && str[i] <= '9') {  // accept one optional sign and digits
        j = j * 10 + (str[i] - '0');  // convert to int
        i++;
    }
    return j;  // return the converted integer value
}
