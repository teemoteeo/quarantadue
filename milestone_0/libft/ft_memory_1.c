/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_memory_1.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/25 12:47:52 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/27 14:06:19 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

void	*ft_memset(void *s, int c, size_t n)
{
	size_t			i;
	unsigned char	*ptr;

	i = 0;
	ptr = (unsigned char *)s;
	while (i < n)
	{
		ptr[i] = (unsigned char)c;
		i++;
	}
	return (s);
}

void	ft_bzero(void *s, size_t n)
{
	size_t			i;
	unsigned char	*ptr;

	i = 0;
	ptr = (unsigned char *)s;
	while (i < n)
	{
		ptr[i] = 0;
		i++;
	}
}

void	*ft_memcpy(void *dst, const void *src, size_t n)
{
	size_t				i;
	unsigned char		*d;
	const unsigned char	*s;

	if (!dst && !src)
		return (NULL);
	i = 0;
	d = (unsigned char *)dst;
	s = (const unsigned char *)src;
	while (i < n)
	{
		d[i] = s[i];
		i++;
	}
	return (dst);
}

void	*ft_memmove(void *dst, const void *src, size_t len)
{
	size_t				i;
	unsigned char		*d;
	const unsigned char	*s;

	if (!dst && !src)
		return (NULL);
	i = 0;
	d = (unsigned char *)dst;
	s = (const unsigned char *)src;
	if (d < s)
	{
		while (i < len)
		{
			d[i] = s[i];
			i++;
		}
		return (dst);
	}
	i = len;
	while (i-- > 0)
	{
		d[i] = s[i];
	}
	return (dst);
}

void	*ft_memchr(const void *s, int c, size_t n)
{
	size_t				i;
	const unsigned char	*ptr;

	i = 0;
	ptr = (const unsigned char *)s;
	while (i < n)
	{
		if (ptr[i] == (unsigned char)c)
			return ((void *)(ptr + i));
		i++;
	}
	return (NULL);
}

// #include <stdio.h>

// int	main(void)
// {
// 	char	*str = ft_calloc(2, 2);
// 	char	src[10] = "due";
// 	char	dst[20] = "quarantadue";
// 	int		i;

// 	printf("%s\n", (char *)ft_memset(str, 'c', 4));
// 	ft_bzero(str, 3);
// 	i = 0;
// 	while (i < 4)
// 	{
// 		printf("%d ", str[i]);
// 		i++;
// 	}
// 	printf("\n");
// 	printf("%s\n", (char *)ft_memcpy(dst, src, 3));
// 	printf("%s\n", (char *)ft_memmove(dst, src, 3));
// 	printf("%s\n", (char *)ft_memchr(dst, 'n', 10));
// }
