/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_printf.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/27 18:25:15 by tcostant          #+#    #+#             */
/*   Updated: 2025/12/02 15:49:14 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ft_printf.h"

static const t_struct	g_list[] = {
{'c', ft_print_char},
{'s', ft_print_str},
{'d', ft_print_nbr},
{'i', ft_print_nbr},
{'p', ft_print_hex_p},
{'u', ft_print_unsigned},
{'x', ft_print_hex_lower},
{'X', ft_print_hex_upper},
{'%', ft_print_literal},
{0, NULL}
};

int	ft_handle_format(const char *format, size_t *i, va_list *args)
{
	size_t	j;
	int		printed_chars;

	j = 0;
	printed_chars = 0;
	while (g_list[j].key)
	{
		if (format[*i + 1] == g_list[j].key)
		{
			printed_chars += g_list[j].f(args);
			*i += 2;
			return (printed_chars);
		}
		j++;
	}
	write(1, &format[*i], 1);
	write(1, &format[*i + 1], 1);
	*i += 2;
	return (2);
}

int	ft_printf(const char *format, ...)
{
	size_t	i;
	va_list	args;
	int		printed_chars;

	if (!format)
		return (-1);
	va_start(args, format);
	i = 0;
	printed_chars = 0;
	while (format[i])
	{
		if (format[i] != '%')
		{
			write(1, &format[i], 1);
			printed_chars++;
			i++;
		}
		else
			printed_chars += ft_handle_format(format, &i, &args);
	}
	va_end(args);
	return (printed_chars);
}

// int	main(void)
// {
// 	char	*str = NULL;
// 	int		var_test = 42;

// 	ft_printf("ft stampa stringa: %s\n", str);
// 	printf("stampa stringa: %s\n", str);
// 	ft_printf("ft stampa carattere: %c\n", 'c');
// 	printf("stampa carattere: %c\n", 'c');
// 	ft_printf("ft stampa stringa: %s\n", "quarantadue");
// 	printf("stampa stringa: %s\n", "quarantadue");
// 	ft_printf("ft stampa numero: %d, %i, %u\n", 42, 50000, -150);
// 	printf("stampa numero: %d, %i, %u\n", 42, 50000, -150);
// 	ft_printf("ft stampa puntatore: %p\n", str);
// 	printf("stampa puntatore: %p\n", str);
// 	ft_printf("ft stampa puntatore: %p\n", &var_test);
// 	printf("stampa puntatore: %p\n", &var_test);
// 	ft_printf("ft stampa esadecimale minuscolo: %x\n", var_test);
// 	printf("stampa esadecimale minuscolo: %x\n", var_test);
// 	ft_printf("ft stampa esadecimale minuscolo: %X\n", var_test);
// 	printf("stampa esadecimale minuscolo: %X\n", var_test);
// }
