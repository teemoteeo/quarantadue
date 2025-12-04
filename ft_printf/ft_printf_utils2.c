/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_printf_utils2.c                                 :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/29 17:50:11 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/30 20:01:38 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ft_printf.h"

//%u
int	ft_print_unsigned(va_list *ap)
{
	unsigned int	n;
	char			*str;
	int				i;

	n = va_arg(*ap, unsigned int);
	str = ft_uitoa(n);
	if (!str)
		return (write(1, "(null)", 6));
	i = 0;
	while (str[i])
		write(1, &str[i++], 1);
	free(str);
	return (i);
}

static int	ft_print_hex_nbr(va_list *ap, char *base)
{
	unsigned int	n;

	n = va_arg(*ap, unsigned int);
	return (ft_putnbr_base(n, base));
}

//%x
int	ft_print_hex_lower(va_list *ap)
{
	return (ft_print_hex_nbr(ap, "0123456789abcdef"));
}
//%X
int	ft_print_hex_upper(va_list *ap)
{
	return (ft_print_hex_nbr(ap, "0123456789ABCDEF"));
}
