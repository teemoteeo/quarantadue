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

/*
 * Anche dongle2 passa dalla coda FIFO/EDF del suo dongle, come dongle1, così
 * non scavalca mai l'ordine di fairness dello scheduler. Se la seconda
 * acquisizione fallisce dongle1 viene rilasciato: l'ordine di Havender regge.
 */
static int	acquire_second_dongle(t_coder *c, t_dongle *dongle1,
				t_dongle *dongle2)
{
	if (scheduler_request_single(c->sim, c->id, dongle2) != 0)
	{
		dongle_release(dongle1);
		return (-1);
	}
	if (check_stop(c->sim))
	{
		dongle_release(dongle1);
		dongle_release(dongle2);
		return (-1);
	}
	log_state(c->sim, c->id, "has taken a dongle");
	return (0);
}

int	acquire_both_dongles(t_coder *c, t_dongle *left, t_dongle *right)
{
	t_dongle	*dongle1;
	t_dongle	*dongle2;

	if (c->left_dongle <= c->right_dongle)
	{
		dongle1 = left;
		dongle2 = right;
	}
	else
	{
		dongle1 = right;
		dongle2 = left;
	}
	if (scheduler_request_single(c->sim, c->id, dongle1) != 0)
		return (-1);
	log_state(c->sim, c->id, "has taken a dongle");
	if (check_stop(c->sim))
	{
		dongle_release(dongle1);
		return (-1);
	}
	if (dongle1 == dongle2)
		return (wait_single_dongle(c, dongle1));
	return (acquire_second_dongle(c, dongle1, dongle2));
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
