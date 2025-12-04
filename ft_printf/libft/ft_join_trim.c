/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_join_trim.c                                     :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/25 17:41:34 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/27 12:50:48 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

char	*ft_strjoin(char const *s1, char const *s2)
{
	char	*result;
	size_t	i;
	size_t	total_len;

	total_len = ft_strlen(s1) + ft_strlen(s2);
	result = malloc((total_len + 1) * sizeof(char));
	if (!result)
		return (NULL);
	i = 0;
	while (*s1)
	{
		result[i] = *s1;
		s1++;
		i++;
	}
	while (*s2)
	{
		result[i] = *s2;
		s2++;
		i++;
	}
	result[i] = '\0';
	return (result);
}

static int	is_charset(char const str, char const *charset)
{
	while (*charset != '\0')
	{
		if (*charset == str)
			return (1);
		charset++;
	}
	return (0);
}

char	*ft_strtrim(char const *str, char const *charset)
{
	char	*trim_str;
	size_t	trim_len;

	while (*str && is_charset(*str, charset))
		str++;
	trim_len = ft_strlen(str);
	while (trim_len > 0 && is_charset(str[trim_len - 1], charset))
		trim_len--;
	trim_str = malloc((trim_len + 1) * sizeof(char));
	if (!trim_str)
		return (NULL);
	trim_str[trim_len] = '\0';
	while (trim_len > 0)
	{
		trim_str[trim_len - 1] = str[trim_len - 1];
		trim_len--;
	}
	return (trim_str);
}

// #include <stdio.h>

// int	main(void)
// {
// 	char	*str1 = "quaranta";
// 	char	*str2 = "due";
// 	char	*str3 = "----ciao----";
// 	char	*str4 = "-";

// 	printf("joined strings: %s\n", ft_strjoin(str1, str2));
// 	printf("trimmed strings: %s\n", ft_strtrim(str3, str4));
// }
