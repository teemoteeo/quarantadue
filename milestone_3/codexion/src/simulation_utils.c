/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   simulation_utils.c                                 :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"

/*
 * Circular layout: coder N sits between dongle N-1 and dongle N.
 * Coder 1 sits between dongle 0 and dongle 1.
 * Coder N sits between dongle N-1 and dongle 0.
 */
void	simulation_init_coders(t_simulation *sim)
{
	int	i;

	i = 0;
	while (i < sim->nb_coders)
	{
		sim->coders[i].id = i + 1;
		sim->coders[i].state = CODER_RUNNING;
		sim->coders[i].compiles_done = 0;
		sim->coders[i].last_compile_start = 0;
		sim->coders[i].sim = sim;
		sim->coders[i].left_dongle = i;
		sim->coders[i].right_dongle = (i + 1) % sim->nb_coders;
		i++;
	}
}

void	simulation_init_dongles(t_simulation *sim)
{
	int	i;

	i = 0;
	while (i < sim->nb_coders)
	{
		dongle_init(&sim->dongles[i], sim);
		i++;
	}
}

void	simulation_spawn_threads(t_simulation *sim)
{
	int	i;

	i = 0;
	while (i < sim->nb_coders)
	{
		pthread_create(&sim->coders[i].thread, NULL,
			coder_routine, &sim->coders[i]);
		i++;
	}
	pthread_create(&sim->monitor_thread, NULL,
		monitor_routine, sim);
}

void	simulation_join_threads(t_simulation *sim)
{
	int	i;

	i = 0;
	while (i < sim->nb_coders)
	{
		pthread_join(sim->coders[i].thread, NULL);
		i++;
	}
	pthread_join(sim->monitor_thread, NULL);
}
