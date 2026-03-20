/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_split.c                                         :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/25 17:56:37 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/27 17:45:47 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

static int	count_words(char *str, char c)
{
	size_t	i;
	int		count;

	i = 0;
	count = 0;
	while (str[i])
	{
		while (str[i] == c)
			i++;
		if (str[i] && str[i] != c)
		{
			count++;
			while (str[i] && str[i] != c)
				i++;
		}
	}
	return (count);
}

static void	free_split(char **result, size_t word_index)
{
	size_t	i;

	i = 0;
	while (i < word_index)
	{
		free(result[i]);
		i++;
	}
	free(result);
}

static char	*malloc_word(char *str, size_t start, size_t end)
{
	size_t		j;
	char		*word;

	word = malloc(((end - start) + 1) * sizeof(char));
	if (!word)
		return (NULL);
	j = 0;
	while (start + j < end)
	{
		word[j] = str[start + j];
		j++;
	}
	word[j] = '\0';
	return (word);
}

static char	**ft_splitstr(char **result, char *str, char c)
{
	size_t		start;
	size_t		i;
	size_t		word_index;

	i = 0;
	word_index = 0;
	while (str[i])
	{
		while (str[i] == c)
			i++;
		if (str[i] == '\0')
			break ;
		start = i;
		while (str[i] != c && str[i] != '\0')
			i++;
		result[word_index] = malloc_word(str, start, i);
		if (!result[word_index])
		{
			free_split(result, word_index);
			return (NULL);
		}
		word_index++;
	}
	result[word_index] = NULL;
	return (result);
}

char	**ft_split(char *str, char c)
{
	char	**result;

	result = malloc((count_words(str, c) + 1) * sizeof(char *));
	if (!result)
		return (NULL);
	result = ft_splitstr(result, str, c);
	return (result);
}

// #include <stdio.h>

// int	main(int argc, char **argv)
// {
// 	if (argc != 2)
// 		return (0);
// 	printf("parole: %d\n", count_words(argv[1], 'c'));
// 	int i = 0;
// 	char **res = ft_split(argv[1], 'c');
// 	while (i < count_words(argv[1], 'c'))
// 	{
// 		printf("%s\n", res[i]);
// 		i++;
// 	}
// }