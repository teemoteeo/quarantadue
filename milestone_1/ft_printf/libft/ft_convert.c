/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_convert.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/24 17:30:28 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/27 12:43:47 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"
#include <stdio.h>

int	ft_atoi(const char *str)
{
	int	i;
	int	nb_final;

	i = 1;
	nb_final = 0;
	while ((*str >= '\t' && *str <= '\r') || *str == ' ')
		str++;
	if (*str == '+' || *str == '-')
	{
		if (*str == '-')
			i *= -1;
		str++;
	}
	while (*str >= '0' && *str <= '9')
	{
		nb_final = (nb_final * 10) + (*str - '0');
		str++;
	}
	return (nb_final * i);
}

static size_t	ft_count_digits(long n)
{
	size_t	counter;

	counter = 0;
	if (n < 0)
	{
		n = -n;
		counter++;
	}
	while (n > 0)
	{
		n /= 10;
		counter++;
	}
	return (counter);
}

static void	ft_write_digits(char *res, long nb, size_t counter)
{
	size_t	i;
	int		is_negative;

	is_negative = 0;
	if (nb < 0)
	{
		nb = -nb;
		is_negative = 1;
	}
	i = counter - 1;
	while (nb > 0)
	{
		res[i] = (nb % 10) + '0';
		nb /= 10;
		i--;
	}
	if (is_negative)
		res[0] = '-';
}

char	*ft_itoa(int n)
{
	long	nb;
	char	*res;
	size_t	counter;

	nb = n;
	if (nb == 0)
	{
		res = malloc(2);
		res[0] = '0';
		res[1] = '\0';
		return (res);
	}
	counter = ft_count_digits(nb);
	res = malloc((counter + 1) * sizeof(char));
	if (!res)
		return (NULL);
	res[counter] = '\0';
	ft_write_digits(res, nb, counter);
	return (res);
}

// int	main(int argc, char** argv)
// {
// 	if (argc != 2)
// 		return (0);
// 	printf("atoi: %d\n", atoi(argv[1]));
// 	printf("ft_atoi: %d\n", ft_atoi(argv[1]));

// 	//printf("itoa: %d", itoa(atoi(argv[1])));
// 	printf("ft_itoa: %s\n", ft_itoa(atoi(argv[1])));
// }