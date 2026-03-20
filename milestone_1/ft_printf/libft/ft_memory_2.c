/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_memory_2.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/25 13:55:13 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/27 13:28:50 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

int	ft_memcmp(const void *s1, const void *s2, size_t n)
{
	size_t				i;
	const unsigned char	*ptr_1;
	const unsigned char	*ptr_2;

	i = 0;
	ptr_1 = (const unsigned char *)s1;
	ptr_2 = (const unsigned char *)s2;
	while (i < n)
	{
		if (ptr_1[i] != ptr_2[i])
			return (ptr_1[i] - ptr_2[i]);
		i++;
	}
	return (0);
}

// #include <stdio.h>

// int	main(void)
// {
// 	char	str1[20] = "quarantadue";
// 	char	str2[20] = "quaraNtadue";

// 	printf("cmp first 5 bytes: %d\n", ft_memcmp(str1, str2, 5));
// 	printf("cmp first 10 bytes: %d\n", ft_memcmp(str1, str2, 10));
// }
