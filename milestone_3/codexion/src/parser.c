/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   parser.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"
#include <string.h>

static int	ft_atoi(const char *s)
{
	long long	n;
	int			sign;

	n = 0;
	sign = 1;
	while (*s == ' ' || (*s >= '\t' && *s <= '\r'))
		s++;
	if (*s == '-' || *s == '+')
	{
		if (*s == '-')
			sign = -1;
		s++;
	}
	while (*s >= '0' && *s <= '9')
	{
		n = n * 10 + (*s - '0');
		s++;
	}
	return ((int)(n * sign));
}

static int	is_valid_number(const char *s)
{
	int			i;
	long long	n;

	i = 0;
	if (s[i] == '-' || s[i] == '+')
		i++;
	if (s[i] == '\0')
		return (0);
	n = 0;
	while (s[i])
	{
		if (s[i] < '0' || s[i] > '9')
			return (0);
		n = n * 10 + (s[i] - '0');
		if (n > 2147483647)
			return (0);
		i++;
	}
	return (1);
}

static int	parse_scheduler(const char *s)
{
	if (strcmp(s, "fifo") == 0)
		return (CODEX_FIFO);
	if (strcmp(s, "edf") == 0)
		return (CODEX_EDF);
	return (-1);
}

static int	parse_and_validate(char **argv, t_simulation *sim)
{
	int	sched;

	if (!is_valid_number(argv[1]) || !is_valid_number(argv[2])
		|| !is_valid_number(argv[3]) || !is_valid_number(argv[4])
		|| !is_valid_number(argv[5]) || !is_valid_number(argv[6])
		|| !is_valid_number(argv[7]))
		return (1);
	sim->nb_coders = ft_atoi(argv[1]);
	sim->time_to_burnout = ft_atoi(argv[2]);
	sim->time_to_compile = ft_atoi(argv[3]);
	sim->time_to_debug = ft_atoi(argv[4]);
	sim->time_to_refactor = ft_atoi(argv[5]);
	sim->compiles_required = ft_atoi(argv[6]);
	sim->dongle_cooldown_ms = ft_atoi(argv[7]);
	sched = parse_scheduler(argv[8]);
	if (sched < 0)
		return (1);
	sim->scheduler_type = (t_scheduler)sched;
	if (sim->nb_coders <= 0 || sim->nb_coders > MAX_CODERS
		|| sim->time_to_burnout < 0
		|| sim->time_to_compile <= 0 || sim->time_to_debug < 0
		|| sim->time_to_refactor < 0 || sim->compiles_required <= 0
		|| sim->dongle_cooldown_ms < 0)
		return (1);
	return (0);
}

int	parse_args(int argc, char **argv, t_simulation *sim)
{
	if (argc != 9)
		return (1);
	return (parse_and_validate(argv, sim));
}
