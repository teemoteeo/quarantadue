/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_putnbr_base.c                                   :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/10/30 13:41:45 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/30 20:02:05 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ft_printf.h"

int	ft_putnbr_base(unsigned long nbr, char *base)
{
	char	buffer[50];
	int		i;
	int		len_base;
	int		count;

	len_base = ft_strlen(base);
	if (len_base < 2)
		return (0);
	if (nbr == 0)
		return (write(1, &base[0], 1));
	i = 0;
	while (nbr > 0)
	{
		buffer[i++] = base[nbr % len_base];
		nbr /= len_base;
	}
	count = 0;
	while (i-- > 0)
		count += write(1, &buffer[i], 1);
	return (count);
}

// int	main(void)
// {
// 	int		n = 442;
// 	char	*base = "0123456789";

// 	ft_putnbr_base(n, base);
// }
