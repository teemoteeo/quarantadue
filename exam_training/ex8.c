/*
** Exercise: rostring
**
** Program name: rostring
** Allowed functions: write, malloc, free
**
** Assignment:
**   Write a program that takes a string and rotates it by moving the
**   first word to the end of the string.
**
**   - A word is defined as a part of a string delimited either by
**     spaces/tabs, or by the start/end of the string.
**   - Words in the output are separated by a single space.
**   - If the number of arguments is not 1, output a newline only.
**   - Extra arguments beyond the first are ignored.
**
** Examples:
**   $> ./rostring "abc   " | cat -e
**   abc$
**
**   $> ./rostring "Que la lumiere soit" | cat -e
**   la lumiere soit Que$
**
**   $> ./rostring "     AkjhZ zLKIJz , 23y" | cat -e
**   zLKIJz , 23y AkjhZ$
**
**   $> ./rostring | cat -e
**   $
*/
/* PSUDOCODE
1. skip whitespace iniziale
2. salva puntatore first_word = &argv[1][i]
3. conta word_len finché non whitespace
4. loop sul resto della stringa:
   - skip whitespace
   - se c'è un char: stampa la parola, poi uno spazio
5. write(1, first_word, word_len)
6. write(1, "\n", 1) */

#include <unistd.h>

static int	is_space(char c)
{
	return (c == ' ' || c == '\t');
}

int	main(int argc, char **argv)
{
	char	*str;
	int		i;
	int		fw_start;
	int		fw_len;
	int		first;
	int		word_start;

	if (argc != 2)
	{
		write(1, "\n", 1);
		return (0);
	}
	str = argv[1];
	i = 0;
	// 1. skip whitespace iniziale
	while (str[i] && is_space(str[i]))
		i++;
	// 2. salva puntatore first_word = &argv[1][i]
	fw_start = i;
	// 3. conta word_len finché non whitespace
	while (str[i] && !is_space(str[i]))
		i++;
	fw_len = i - fw_start;
	// 4. loop sul resto della stringa
	first = 1;
	while (str[i])
	{
		// - skip whitespace
		while (str[i] && is_space(str[i]))
			i++;
		// - se c'è un char: stampa la parola, poi uno spazio
		if (str[i])
		{
			word_start = i;
			while (str[i] && !is_space(str[i]))
				i++;
			if (!first)
				write(1, " ", 1);
			write(1, str + word_start, i - word_start);
			first = 0;
		}
	}
	// 5. write(1, first_word, word_len)
	if (fw_len > 0)
	{
		if (!first)
			write(1, " ", 1);
		write(1, str + fw_start, fw_len);
	}
	// 6. write(1, "\n", 1)
	write(1, "\n", 1);
	return (0);
}
