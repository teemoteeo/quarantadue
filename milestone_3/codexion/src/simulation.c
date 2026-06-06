/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   simulation.c                                       :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#              */
/*   Updated: 2026/06/04 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

#include "codexion.h"
#include <sys/time.h>
#include <unistd.h>

void	ft_usleep(long long ms)
{
	usleep((useconds_t)(ms * 1000));
}

void	simulation_init(t_simulation *sim)
{
	sim->stop_flag = 0;
	pthread_mutex_init(&sim->stop_mutex, NULL);
	pthread_mutex_init(&sim->log_mutex, NULL);
	pthread_mutex_init(&sim->sched_mutex, NULL);
	heap_init(sim);
	simulation_init_dongles(sim);
	simulation_init_coders(sim);
}

static void	simulation_record_start(t_simulation *sim)
{
	struct timeval	tv;

	gettimeofday(&tv, NULL);
	sim->start_time = (long long)tv.tv_sec * 1000 + tv.tv_usec / 1000;
}

void	simulation_run(t_simulation *sim)
{
	simulation_record_start(sim);
	simulation_init_last_compile(sim);
	simulation_spawn_threads(sim);
	simulation_join_threads(sim);
}

void	simulation_cleanup(t_simulation *sim)
{
	int	i;

	i = 0;
	while (i < sim->nb_coders)
	{
		dongle_destroy(&sim->dongles[i]);
		i++;
	}
	pthread_mutex_destroy(&sim->stop_mutex);
	pthread_mutex_destroy(&sim->log_mutex);
	pthread_mutex_destroy(&sim->sched_mutex);
	heap_destroy(sim);
}
