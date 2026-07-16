#include <stddef.h>

int ft_isascii(int c) {
    // Check if the ASCII code point is within the range 0-127
    return c >= 'a' && c <= 'z';
}
