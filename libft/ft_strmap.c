/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_strmap.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/26 12:09:23 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/26 13:22:07 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

char	*ft_strmapi(char const *s, char (*f)(unsigned int, char))
{
	unsigned int	i;
	char			*result;

	i = 0;
	result = malloc((ft_strlen(s) + 1) * sizeof(char));
	if (!result)
		return (NULL);
	while (s[i])
	{
		result[i] = f(i, s[i]);
		i++;
	}
	result[i] = '\0';
	return (result);
}

void	ft_striteri(char *s, void (*f)(unsigned int, char *))
{
	unsigned int	i;

	i = 0;
	while (s[i])
	{
		f(i, &s[i]);
		i++;
	}
}

// static void	alternate_case_iter(unsigned int i, char *c)
// {
// 	if (i % 2 == 0)static void	alternate_case_iter(unsigned int i, char *c)
// {
// 	if (i % 2 == 0)
// 	{
// 		if (*c >= 'a' && *c <= 'z')
// 			*c -= 32;
// 	}
// 	else
// 	{
// 		if (*c >= 'A' && *c <= 'Z')
// 			*c += 32;
// 	}
// }

// static char	alternate_case_map(unsigned int i, char c)
// {
// 	if (i % 2 == 0)
// 	{
// 		if (c >= 'a' && c <= 'z')
// 			return (c - 32);
// 		return (c);
// 	}
// 	else
// 	{
// 		if (c >= 'A' && c <= 'Z')
// 			return (c + 32);
// 		return (c);
// 	}
// }
// 	{
// 		if (*c >= 'a' && *c <= 'z')
// 			*c -= 32;
// 	}
// 	else
// 	{
// 		if (*c >= 'A' && *c <= 'Z')
// 			*c += 32;
// 	}
// }

// static char	alternate_case_map(unsigned int i, char c)
// {
// 	if (i % 2 == 0)
// 	{
// 		if (c >= 'a' && c <= 'z')
// 			return (c - 32);
// 		return (c);
// 	}
// 	else
// 	{
// 		if (c >= 'A' && c <= 'Z')
// 			return (c + 32);
// 		return (c);
// 	}
// }

// #include <stdio.h>
// int	main(int argc, char **argv)
// {
// 	if(argc != 2)
// 		return (0);
// 	printf("stringa iniziale: %s\n", argv[1]);
// 	ft_striteri(argv[1], alternate_case_2);
// 	printf("new stringa: %s\n", argv[1]);
// }
