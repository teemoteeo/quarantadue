/*
** Assignment name : ft_split
**
** Expected files  : ft_split.c
** Allowed functions: malloc
**
** -----------------------------------------------------------------------
**
** Write a function that splits a string into words and returns them as a
** NULL-terminated array of strings.
**
** Words are segments separated by spaces, tabs (\t), or newlines (\n).
**
** Function prototype:
**   char **ft_split(char *str);
**
** The returned array must be NULL-terminated.
**
** Example:
**   ft_split("  hello   world  foo  ")
**   => ["hello", "world", "foo", NULL]
**
**   ft_split("")
**   => [NULL]
*/

/*
** PSEUDOCODE
** ----------
**
** is_space(c):
**   return true if c is ' ', '\t', or '\n'
**
** word_len(str, i):
**   count characters from str[i] until a space or '\0' is hit
**   return that count
**
** count_words(str):
**   i = 0, words = 0
**   loop while str[i]:
**     skip all spaces (advance i)
**     if str[i] is not '\0':
**       words++
**       skip all non-spaces (advance i past the word)
**   return words
**
** ft_split(str):
**   allocate res = array of (count_words(str) + 1) char* pointers
**   i = 0  (index into str)
**   j = 0  (index into res)
**   loop while str[i]:
**     skip spaces  -> advance i
**     if str[i] != '\0':
**       len = word_len(str, i)
**       allocate res[j] of size len + 1
**       copy len chars from str[i..] into res[j]
**       null-terminate res[j]
**       i += len, j++
**   res[j] = NULL   <- sentinel
**   return res
*/

#include <stdlib.h>

static int	is_space(char c)
{
	return (c == ' ' || c == '\t' || c == '\n');
}

static int	word_len(char *str, int i)
{
	int	len;

	len = 0;
	while (str[i + len] && !is_space(str[i + len]))
		len++;
	return (len);
}

static int	count_words(char *str)
{
	int	i;
	int	words;

	i = 0;
	words = 0;
	while (str[i])
	{
		while (str[i] && is_space(str[i]))
			i++;
		if (str[i])
		{
			words++;
			while (str[i] && !is_space(str[i]))
				i++;
		}
	}
	return (words);
}

char	**ft_split(char *str)
{
	char	**res;
	int		i;
	int		j;
	int		k;
	int		len;

	res = malloc(sizeof(char *) * (count_words(str) + 1));
	i = 0;
	j = 0;
	while (str[i])
	{
		while (str[i] && is_space(str[i]))
			i++;
		if (str[i])
		{
			len = word_len(str, i);
			res[j] = malloc(len + 1);
			k = 0;
			while (k < len)
				res[j][k++] = str[i++];
			res[j][k] = '\0';
			j++;
		}
	}
	res[j] = NULL;
	return (res);
}

#include <stdio.h>

int	main(void)
{
	char	**res;
	int		i;

	char *tests[] = {
		"  hello   world  foo  ",
		"",
		"   ",
		"one",
		"\thello\nworld",
		NULL
	};

	i = 0;
	while (tests[i])
	{
		printf("ft_split(\"%s\"):\n", tests[i]);
		res = ft_split(tests[i]);
		int j = 0;
		while (res[j])
		{
			printf("  [%s]\n", res[j]);
			free(res[j]);
			j++;
		}
		free(res);
		printf("  word count: %d\n\n", j);
		i++;
	}
	return (0);
}
