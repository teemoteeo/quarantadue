/*
** Assignment name : add_prime_sum
**
** Expected files  : add_prime_sum.c
** Allowed functions: write, exit
**
** ---------------------------------------------------------------------------
**
** Write a program that takes a positive integer as argument and displays the
** sum of all prime numbers inferior or equal to it followed by a newline.
**
** If the number of arguments is not 1, or the argument is not a positive
** number, just display 0 followed by a newline.
**
** Examples:
**   $>./add_prime_sum 5
**   10
**
**   $>./add_prime_sum 7 | cat -e
**   17$
**
**   $>./add_prime_sum | cat -e
**   0$
*/

#include <unistd.h>
#include <stdlib.h>

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

void	ft_putnbr(int nb)
{
	char c;
	if (nb == -2147483648)
	{
		write(1, "-2147483648", 11);
		return ;
	}
	if (nb < 0)
	{
		write(1, "-", 1);
		nb = nb * -1;
	}
	if (nb >= 0 && nb < 10)
	{
		c = nb + '0';
		write(1, &c, 1);
	}
	else
	{
		ft_putnbr(nb / 10);
		ft_putnbr(nb % 10);
	}
}

int	ft_is_prime(int nb)
{
	int	i;

	if (nb <= 1)
		return (0);
	i = 2;
	while (i < nb) {
		if (nb % i == 0)
			return (0);
		i++;
	}
	return (1);
}

int	main(int argc, char **argv)
{
	if (argc != 2)
	{
		write(1, "0\n", 2);
		return (0);
	}

	int num = ft_atoi(argv[1]);
	if (num <= 0)
	{
		write(1, "0\n", 2);
		return (0);
	}

	int result = 0;
	int i = 2;

	while (i <= num)
	{
		if (ft_is_prime(i))
			result += i;
		i++;
	}
	ft_putnbr(result);
	write(1, "\n", 1);
	return (0);
}
