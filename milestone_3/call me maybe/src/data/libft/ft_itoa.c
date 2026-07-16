#include <stddef.h>  // for size_t, NULL

#include <stdlib.h>
#include <unistd.h>

char *ft_itoa(int n) {
    if (n == INT_MIN || n == -INT_MIN) {
        return NULL;  // handle INT_MIN and negative numbers
    }

    char *str = (char *)malloc(sizeof(char) * 32);  // allocate memory for the string
    if (!str) {
        return NULL;  // allocation failure
    }

    int i = 0;
    while (n > 0) {
        n /= 10;  // divide by 10 to remove the last digit
        str[i++] = '0' + n % 10;  // append the last digit to the string
    }

    str[i] = '\0';  // ensure null termination

    return str;  // return the allocated string
}
