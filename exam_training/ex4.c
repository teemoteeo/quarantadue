/*
** Exercise: ft_atoi
**
** Prototype: int ft_atoi(const char *str);
** Allowed functions: None
**
** Description:
**   Write a function that converts the string argument str to an integer
**   and returns it.
**   - Handle leading whitespace (' ', '\t', '\n', '\v', '\f', '\r')
**   - Handle one optional '+' or '-' sign
**   - Stop at the first non-digit character after the number
**
** Examples:
**   ft_atoi("42")        -> 42
**   ft_atoi("  -13")     -> -13
**   ft_atoi("  +50abc")  -> 50
**   ft_atoi("")          -> 0
*/

#include <stdio.h>

int	ft_atoi(const char *str)
{
	/* your code here */
	int i = 0;
	int nb = 0;
	int sign = 1;

	while (str[i] == ' ' || str[i] == '\t' || str[i] == '\n' ||
			str[i] == '\v' || str[i] == '\f' || str[i] == '\r') {
		i++;
	}
	while (str[i] == '+' || str[i] == '-') {
		if (str[i] == '-')
			sign *= -1;
		i++;
	}
	while (str[i] >= '0' && str[i] <= '9') {
		nb = (nb * 10) + (str[i] - '0');
		i++;		
	}
	return (nb * sign);
}

int	main(void) {
	printf("%d\n", ft_atoi("---++2345"));
	return (0);
}
