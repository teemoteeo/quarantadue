/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_printf.h                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/27 18:34:51 by tcostant          #+#    #+#             */
/*   Updated: 2025/12/10 12:50:45 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#ifndef FT_PRINTF_H
# define FT_PRINTF_H

# include <unistd.h>
# include <stdlib.h>
# include <stddef.h>
# include <stdlib.h>
# include <stdarg.h>
# include <stdio.h>
# include "libft/libft.h"

int		ft_printf(const char *format, ...);

int		ft_print_char(va_list *ap);
int		ft_print_str(va_list *ap);
int		ft_print_nbr(va_list *ap);
int		ft_print_hex_p(va_list *ap);
int		ft_print_unsigned(va_list *ap);
int		ft_print_literal(va_list *ap);
int		ft_print_hex_lower(va_list *ap);
int		ft_print_hex_upper(va_list *ap);

int		ft_putnbr_base(unsigned long nbr, char *base);
char	*ft_uitoa(unsigned int n);

#endif
