/* ************************************************************************** */
/*                                                                            */
/*                                                        :::      ::::::::   */
/*   coder_utils.c                                      :+:      :+:    :+:   */
/*                                                    +:+ +:+         +:+     */
/*   By: teemoteeo <teemoteeo@student.42.fr>        +#+  +:+       +#+        */
/*                                                +#+#+#+#+#+   +#+           */
/*   Created: 2026/06/04 00:00:00 by teemoteeo        #+#    #+#             */
/*   Updated: 2026/06/19 00:00:00 by teemoteeo       ###   ########.fr       */
/*                                                                            */
/* ************************************************************************** */

/* Logica di acquisizione dei dongle per un coder (ordinata per escludere il
 * deadlock), più getter/setter del flag di stop condiviso. */

#include "codexion.h"

/*
 * Coder singolo: esiste un solo dongle, quindi non se ne possono tenere due
 * contemporaneamente. Il coder tiene il suo unico dongle e aspetta che il
 * monitor segnali il burnout.
 */
static int	wait_single_dongle(t_coder *c, t_dongle *dongle1)
{
	while (!check_stop(c->sim))
		ft_usleep(1);
	dongle_release(dongle1);
	return (-1);
}

/* Restituisce sempre -1: la coppia è stata presa ma la simulazione è finita. */
static int	release_and_fail(t_dongle *dongle1, t_dongle *dongle2)
{
	dongle_release(dongle1);
	if (dongle1 != dongle2)
		dongle_release(dongle2);
	return (-1);
}

/*
 * I due dongle vengono ordinati per indice crescente e poi richiesti come
 * coppia atomica: o li si prende entrambi, o non se ne prende nessuno.
 * Così il coder non resta mai fermo con un dongle in mano ad aspettarne un
 * altro, e il vicino che aspetta quel dongle non va in starvation.
 * L'ordine crescente serve ancora, ma solo per prendere i due mutex sempre
 * nello stesso verso dentro dongle_try_acquire_pair.
 */
int	acquire_both_dongles(t_coder *c, t_dongle *left, t_dongle *right)
{
	t_dongle	*dongle1;
	t_dongle	*dongle2;

	dongle1 = left;
	dongle2 = right;
	if (c->left_dongle > c->right_dongle)
	{
		dongle1 = right;
		dongle2 = left;
	}
	if (scheduler_request_pair(c->sim, c->id, dongle1, dongle2) != 0)
		return (-1);
	log_state(c->sim, c->id, "has taken a dongle");
	if (dongle1 != dongle2)
		log_state(c->sim, c->id, "has taken a dongle");
	if (dongle1 == dongle2)
		return (wait_single_dongle(c, dongle1));
	if (check_stop(c->sim))
		return (release_and_fail(dongle1, dongle2));
	return (0);
}

int	check_stop(t_simulation *sim)
{
	int	stopped;

	pthread_mutex_lock(&sim->stop_mutex);
	stopped = sim->stop_flag;
	pthread_mutex_unlock(&sim->stop_mutex);
	return (stopped);
}

void	set_stop(t_simulation *sim)
{
	pthread_mutex_lock(&sim->stop_mutex);
	sim->stop_flag = 1;
	pthread_mutex_unlock(&sim->stop_mutex);
}
