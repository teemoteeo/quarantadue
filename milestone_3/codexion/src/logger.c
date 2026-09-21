/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   logger.c                                           :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+    */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#   #+#             */
/*   Updated: 2026/06/19 00:00:00 by teemoteeo        ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

/* Log thread-safe: ogni riga "timestamp coder_id messaggio" esce con una
 * sola printf, tenuta sotto log_mutex così due messaggi non si mescolano. */

#include "codexion.h"
#include <stdio.h>

static long long	timestamp_ms(const t_simulation *sim)
{
	return (now_ms() - sim->start_time);
}

static void	print_locked(t_simulation *sim, int coder_id, const char *msg)
{
	printf("%lld %d %s\n", timestamp_ms(sim), coder_id, msg);
}

/* Log forzato (monitor / burnout): sempre stampato. */
void	log_msg(t_simulation *sim, int coder_id, const char *msg)
{
	pthread_mutex_lock(&sim->log_mutex);
	print_locked(sim, coder_id, msg);
	pthread_mutex_unlock(&sim->log_mutex);
}

/*
 * Log dello stato del coder: ignorato se la simulazione è già ferma, così
 * nessuna riga di stato può apparire dopo il messaggio finale "burned out".
 */
void	log_state(t_simulation *sim, int coder_id, const char *msg)
{
	pthread_mutex_lock(&sim->log_mutex);
	if (check_stop(sim))
	{
		pthread_mutex_unlock(&sim->log_mutex);
		return ;
	}
	print_locked(sim, coder_id, msg);
	pthread_mutex_unlock(&sim->log_mutex);
}
