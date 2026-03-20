/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   ft_char_1.c                                        :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: tcostant <tcostant@student.42.fr>          +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2025/11/24 17:50:45 by tcostant          #+#    #+#             */
/*   Updated: 2025/11/25 12:00:05 by tcostant         ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "libft.h"

int	ft_isalpha(int c)
{
	if (('a' <= c && 'z' >= c) || ('A' <= c && 'Z' >= c))
		return (1);
	return (0);
}

int	ft_isdigit(int c)
{
	if ('0' <= c && '9' >= c)
		return (1);
	return (0);
}

int	ft_isalnum(int c)
{
	if (('a' <= c && 'z' >= c) || ('A' <= c && 'Z' >= c)
		|| ('0' <= c && '9' >= c))
		return (1);
	return (0);
}

int	ft_isascii(int c)
{
	if (0 <= c && 127 >= c)
		return (1);
	return (0);
}

int	ft_isprint(int c)
{
	if (32 <= c && c <= 126)
		return (1);
	return (0);
}
