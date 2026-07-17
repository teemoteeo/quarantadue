/*
** Assignment name : ft_rrange
**
** Expected files  : ft_rrange.c
** Allowed functions: malloc
**
** ---------------------------------------------------------------------------
**
** Write the following function:
**
**   int *ft_rrange(int start, int end);
**
** It must allocate (with malloc()) an array of integers, fill it with
** consecutive values that begin at end and end at start (including start
** and end!), then return a pointer to the first value of the array.
**
** Examples:
**   ft_rrange(1,  3)  → [3, 2, 1]
**   ft_rrange(-1, 2)  → [2, 1, 0, -1]
**   ft_rrange(0,  0)  → [0]
**   ft_rrange(0, -3)  → [-3, -2, -1, 0]
*/

#include <stdlib.h>
#include <stdio.h>

int	*ft_rrange(int start, int end)
{
	/* your code here */
	int *range;
	int size = 0;
	int i = 0;
	if (start > end) {
		size = start - end;
		range = malloc((size + 1) * sizeof(int));
		while (i <= size) {
			range[i] = start - i;
			i++;
		}
	} else if (end > start) {
		size = end - start;
		range = malloc((size + 1) * sizeof(int));
		while (i <= size) {
			range[i] = end - i;
			i++;
		}
	} else if (end == start) {
		range = malloc(sizeof(int));
		range[i] = start;
	}
	return range;
}

int	main(void) {
	int *range = ft_rrange(4, 16);
	int i = 0;
	int size = 16 - 4 + 1;

	while (i < size) {
		printf("%d |", range[i]);
		i++;
	}
	write(1, "\n", 1);
}
