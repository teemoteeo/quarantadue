/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_printf_utils1.c                                 :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/27 19:25:10 by tcostant          #+#    #+#             */
/*   Updated: 2025/12/01 12:44:21 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ft_printf.h"

//%c
int	ft_print_char(va_list *ap)
{
	int	c;

	c = va_arg(*ap, int);
	write(1, &c, 1);
	return (1);
}

//%s
int	ft_print_str(va_list *ap)
{
	int		i;
	char	*str;

	i = 0;
	str = va_arg(*ap, char *);
	if (!str)
		return (write(1, "(null)", 6));
	while (str[i])
	{
		write(1, &str[i], 1);
		i++;
	}
	return (i);
}

//%d/%i
int	ft_print_nbr(va_list *ap)
{
	int		n;
	int		i;
	char	*nbr;

	n = va_arg(*ap, int);
	nbr = ft_itoa(n);
	if (!nbr)
	{
		write(1, "(null)", 6);
		return (6);
	}
	i = 0;
	while (nbr[i])
	{
		write(1, &nbr[i], 1);
		i++;
	}
	free(nbr);
	return (i);
}

//%p
int	ft_print_hex_p(va_list *ap)
{
	void			*ptr;
	unsigned long	addr;
	int				count;

	ptr = va_arg(*ap, void *);
	if (!ptr)
		return (write(1, "(nil)", 5));
	addr = (unsigned long)ptr;
	count = 0;
	count += write(1, "0x", 2);
	count += ft_putnbr_base(addr, "0123456789abcdef");
	return (count);
}

//%%
int	ft_print_literal(va_list *ap)
{
	(void)ap;
	write(1, "%", 1);
	return (1);
}
