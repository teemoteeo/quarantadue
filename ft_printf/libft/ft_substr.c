/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_substr.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/24 17:32:38 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/27 14:03:28 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

char	*ft_substr(const char *s, unsigned int start, size_t len)
{
	char	*sub_string;
	size_t	i;

	i = 0;
	if (start >= ft_strlen(s))
		return (ft_strdup(""));
	if (len > ft_strlen(s + start))
		len = ft_strlen(s + start);
	sub_string = malloc((len + 1) * sizeof(char));
	if (!sub_string)
		return (NULL);
	while (i < len)
	{
		sub_string[i] = s[start + i];
		i++;
	}
	sub_string[len] = '\0';
	return (sub_string);
}

// #include <stdio.h>

// int	main(void)
// {
// 	char	str[20] = "quarantadue";

// 	printf("%s\n", ft_substr(str, 3, 6));
// }
