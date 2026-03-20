/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_string_2.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/24 17:24:48 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/27 13:55:44 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

size_t	ft_strlcpy(char *dest, const char *src, size_t size)
{
	size_t	i;

	i = 0;
	if (size > 0)
	{
		while (src[i] && i < size - 1)
		{
			dest[i] = src[i];
			i++;
		}
		dest[i] = '\0';
	}
	i = 0;
	while (src[i])
		i++;
	return (i);
}

size_t	ft_strlcat(char *dest, const char *src, size_t size)
{
	size_t	d_len;
	size_t	s_len;
	size_t	i;

	d_len = ft_strlen(dest);
	s_len = ft_strlen(src);
	i = 0;
	if (size <= d_len)
		return (size + s_len);
	while (src[i] && (d_len + i < size - 1))
	{
		dest[d_len + i] = src[i];
		i++;
	}
	dest[d_len + i] = '\0';
	return (d_len + s_len);
}

char	*ft_strdup(const char *src)
{
	size_t	i;
	size_t	size;
	char	*p;

	i = 0;
	size = ft_strlen(src);
	p = malloc((size + 1) * sizeof(char));
	if (!p)
		return (NULL);
	while (i < size)
	{
		p[i] = src[i];
		i++;
	}
	p[i] = '\0';
	return (p);
}

char	*ft_strnstr(const char *big, const char *little, size_t len)
{
	size_t	i;
	size_t	j;

	if (!little[0])
		return ((char *)big);
	i = 0;
	while (big[i] && i < len)
	{
		j = 0;
		while (big[i + j] && little[j] && i + j < len
			&& big[i + j] == little[j])
			j++;
		if (!little[j])
			return ((char *)&big[i]);
		i++;
	}
	return (NULL);
}

// #include <stdio.h>

// int	main(void)
// {
// 	char	dst[20] = "quarantadue";
// 	char	src[10] = "cinquanta";
// 	char	little[10] = "nta";
// 	char	*str_all = ft_strdup(dst);

// 	printf("%ld\n", ft_strlcpy(dst, src, 10));
// 	printf("%s\n", dst);
// 	printf("%ld\n", ft_strlcat(dst, src, 10));
// 	printf("%s\n", dst);
// 	printf("%s\n", str_all);
// 	free(str_all);
// 	printf("%s\n", ft_strnstr("quarantadue", little, 15));
// }