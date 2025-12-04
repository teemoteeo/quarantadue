/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_alloc.c                                         :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/25 14:01:01 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/27 12:42:39 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"
#include <stdint.h>

void	*ft_calloc(size_t count, size_t size)
{
	void	*result;

	if (size != 0 && count > SIZE_MAX / size)
		return (NULL);
	result = malloc(count * size);
	if (!result)
		return (NULL);
	ft_bzero(result, (size * count));
	return (result);
}

// #include <stdio.h>

// int	main(void)
// {
// 	char	*str;
// 	int		i;

// 	i = 0;
// 	str = ft_calloc(2, 2);
// 	while (i < 4)
// 	{
// 		printf("%d", str[i]);
// 		i++;
// 	}
// 	printf("\n");
// }