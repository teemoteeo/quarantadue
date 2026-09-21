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

/* Ciclo di vita della simulazione: inizializza i mutex, registra il tempo di
 * partenza, crea e unisce tutti i thread e alla fine libera le risorse. */

#include "codexion.h"

/* Attesa attiva a passi di mezzo ms: usleep da solo sfora troppo. */
void	ft_usleep(long long ms)
{
	long long	start;

	start = now_ms();
	while (now_ms() - start < ms)
		usleep(500);
}

void	simulation_init(t_simulation *sim)
{
	sim->stop_flag = 0;
	pthread_mutex_init(&sim->stop_mutex, NULL);
	pthread_mutex_init(&sim->log_mutex, NULL);
	pthread_mutex_init(&sim->state_mutex, NULL);
	simulation_init_state(sim);
}

static void	simulation_record_start(t_simulation *sim)
{
	int	i;

	sim->start_time = now_ms();
	i = 0;
	while (i < sim->nb_coders)
	{
		sim->coders[i].last_compile_start = sim->start_time;
		i++;
	}
}

void	simulation_run(t_simulation *sim)
{
	simulation_record_start(sim);
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
	pthread_mutex_destroy(&sim->state_mutex);
}
