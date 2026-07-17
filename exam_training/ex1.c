/*
** Exercise: repeat_alpha
**
** Program name: repeat_alpha
** Allowed functions: write
**
** Description:
**   Write a program that takes a string and displays it, repeating each
**   alphabetical character as many times as its position in the alphabet,
**   followed by a newline.
**   'a' and 'A' are at position 1, 'b' and 'B' at position 2, etc.
**   Case remains unchanged.
**   If the number of arguments is not 1, display only a newline.
**
** Examples:
**   $> ./repeat_alpha "abc"
**   abbccc
**   $> ./repeat_alpha "Alex."
**   Alllllllllllleeeeexxxxxxxxxxxxxxxxxxxxxxxx.
**   $> ./repeat_alpha "aA"
**   aA
**   $> ./repeat_alpha ""
**
**   $> ./repeat_alpha | cat -e
**   $
*/

#include <unistd.h>

int	main(int argc, char **argv)
{
	/* your code here */
	if (argc != 2) {
		write(1, "\n", 1);
		return (0);
	}
	int multiplier = 0;
	int i = 0;
	while (argv[1][i]) {
		if (argv[1][i] >= 'a' && 'z' >= argv[1][i])
			multiplier = argv[1][i] - 96;
		else if (argv[1][i] >= 'A' && 'Z' >= argv[1][i])
			multiplier = argv[1][i] - 64;
		else
			write(1, &argv[1][i], 1);
		while (multiplier > 0) {
			write(1, &argv[1][i], 1);
			multiplier--;
		}
		i++;
	}
	write(1, "\n", 1);
	return (0);
}
