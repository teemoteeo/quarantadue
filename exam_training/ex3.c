/*
** Exercise: search_and_replace
**
** Program name: search_and_replace
** Allowed functions: write
**
** Description:
**   Write a program that takes 3 arguments:
**   - A string to scan
**   - A character to search for (single char)
**   - A character to replace it with (single char)
**   Display the string with every occurrence of the second argument replaced
**   by the third, followed by a newline.
**   If the number of arguments is not 3, display only a newline.
**
** Examples:
**   $> ./search_and_replace "Hello World" "o" "0"
**   Hell0 W0rld
**   $> ./search_and_replace "abc" "b" "B"
**   aBc
**   $> ./search_and_replace | cat -e
**   $
*/

#include <unistd.h>

int	main(int argc, char **argv)
{
	/* your code here */
	if (argc != 4) {
		write(1, "\n", 1);
		return (0);
	}
	int i = 0;
	while (argv[1][i]) {
		if (argv[1][i] == argv[2][0])
			argv[1][i] = argv[3][0];
		write(1, &argv[1][i], 1);
		i++;
	}
	write(1, "\n", 1);
	return (0);
}
