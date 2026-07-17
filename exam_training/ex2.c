/*
** Exercise: rot_13
**
** Program name: rot_13
** Allowed functions: write
**
** Description:
**   Write a program that takes a string and displays it, replacing each
**   alphabetical character by the character 13 places ahead in the alphabet,
**   followed by a newline.
**   If the character would go past 'z' or 'Z', it wraps around.
**   Case remains unchanged.
**   If the number of arguments is not 1, display only a newline.
**
** Examples:
**   $> ./rot_13 "abc"
**   nop
**   $> ./rot_13 "Hello World!"
**   Uryyb Jbeyq!
**   $> ./rot_13 ""
**
**   $> ./rot_13 | cat -e
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
	int i = 0;
	int sub = 0;
	while (argv[1][i]) {
		if (argv[1][i] >= 'a' && 'z' >= argv[1][i]) {
			sub = argv[1][i] + 13;
			if (sub > 'z')
				sub -= 26;
			write(1, &sub, 1);
		}
		else if (argv[1][i] >= 'A' && 'Z' >= argv[1][i]) {
			sub = argv[1][i] + 13;
			if (sub > 'Z')
				sub -= 26;
			write(1, &sub, 1);
		}
		else
			write(1, &argv[1][i], 1);
		i++;
	}
	write(1, "\n", 1);
	return (0);
}
