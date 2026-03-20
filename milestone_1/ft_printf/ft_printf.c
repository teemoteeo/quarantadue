/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_printf.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/27 18:25:15 by tcostant          #+#    #+#             */
/*   Updated: 2025/12/17 14:36:54 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "ft_printf.h"

int static	(*get_function(char c))(va_list *args)
{
	if (c == 'c')
		return (ft_print_char);
	else if (c == 's')
		return (ft_print_str);
	else if (c == 'd')
		return (ft_print_nbr);
	else if (c == 'i')
		return (ft_print_nbr);
	else if (c == 'p')
		return (ft_print_hex_p);
	else if (c == 'u')
		return (ft_print_unsigned);
	else if (c == 'x')
		return (ft_print_hex_lower);
	else if (c == 'X')
		return (ft_print_hex_upper);
	else if (c == '%')
		return (ft_print_literal);
	return (NULL);
}

// int	get_function(char c, va_list *args)
// {
// 	if (c == 'c')
// 		return (ft_print_char(args));
// 	else if (c == 's')
// 		return (ft_print_str(args));
// 	else if (c == 'd')
// 		return (ft_print_nbr(args));
// 	else if (c == 'i')
// 		return (ft_print_nbr(args));
// 	else if (c == 'p')
// 		return (ft_print_hex_p(args));
// 	else if (c == 'u')
// 		return (ft_print_unsigned(args));
// 	else if (c == 'x')
// 		return (ft_print_hex_lower(args));
// 	else if (c == 'X')
// 		return (ft_print_hex_upper(args));
// 	else if (c == '%')
// 		return (ft_print_literal(args));
// 	return (NULL);
// }

int	ft_handle_format(const char *format, size_t *i, va_list *args)
{
	int	(*func)(va_list *);
	int	printed_chars;

	func = get_function(format[*i + 1]);
	printed_chars = 0;
	if (func != NULL)
	{
		printed_chars = func(args);
		*i += 2;
		return (printed_chars);
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
// 	//int		var_test = 42;

// 	ft_printf("ft stampa stringa: %s\n", str);
// 	printf("stampa stringa: %s\n", str);
// 	ft_printf("ft stampa carattere: %c\n", 'c');
// 	printf("stampa carattere: %c\n", 'c');
// 	ft_printf("ft stampa stringa: %s\n", "quarantadue");
// 	printf("stampa stringa: %s\n", "quarantadue");
// 	// ft_printf("ft stampa numero: %d, %i, %u\n", 42, 50000, -150);
// 	// printf("stampa numero: %d, %i, %u\n", 42, 50000, -150);
// 	// ft_printf("ft stampa puntatore: %p\n", str);
// 	// printf("stampa puntatore: %p\n", str);
// 	// ft_printf("ft stampa puntatore: %p\n", &var_test);
// 	// printf("stampa puntatore: %p\n", &var_test);
// 	// ft_printf("ft stampa esadecimale minuscolo: %x\n", var_test);
// 	// printf("stampa esadecimale minuscolo: %x\n", var_test);
// 	// ft_printf("ft stampa esadecimale minuscolo: %X\n", var_test);
// 	// printf("stampa esadecimale minuscolo: %X\n", var_test);
// }
