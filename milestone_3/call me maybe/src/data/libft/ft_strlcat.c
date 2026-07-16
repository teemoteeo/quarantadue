#include <stddef.h>
#include <stdlib.h>

size_t ft_strlcat(char *dst, const char *src, size_t dstsize) {
  // Allocate memory for the result string
  char *result = (char *)malloc(dstsize + sizeof(char) - dstsize);
  if (!result) {
    // If memory allocation fails, return the maximum length of dst
    return dstsize;
  }

  // Copy src to result, NUL-terminating the string
  memcpy(result + dstsize, src, sizeof(char) * (dstsize - strlen(src)));
  result[dstsize] = '\0';

  // Calculate the length of the string to be created
  size_t len = dstsize - strlen(src);

  // Allocate memory for the new string and copy src to it
  char *new_result = (char *)malloc(len + sizeof(char) - len);
  if (!new_result) {
    // If memory allocation fails, return the maximum length of dst
    return len;
  }

  memcpy(new_result + len, src, sizeof(char) * (len - strlen(src)));
  new_result[len] = '\0';

  // Free the memory for result and src
  free(result);
  free(new_result);

  return len;
}
